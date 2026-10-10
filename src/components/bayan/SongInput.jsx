import { useEffect, useRef, useState } from 'react';
import { ExternalLink, Loader2, Music, Youtube } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import buildAccompaniment from './buildAccompaniment';
import LibraryInput from './LibraryInput';

async function readResponse(response) {
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Не удалось обработать запись.');
  return data;
}
function savedJob(value) {
  try {
    if (value === undefined) return sessionStorage.getItem('bayanflow-job');
    if (value) sessionStorage.setItem('bayanflow-job', value);
    else sessionStorage.removeItem('bayanflow-job');
  } catch { /* Playback still works when browser storage is unavailable. */ }
  return '';
}
function pause(signal) {
  return new Promise((resolve, reject) => {
    const abort = () => { clearTimeout(timer); reject(new DOMException('Cancelled', 'AbortError')); };
    const timer = setTimeout(() => { signal.removeEventListener('abort', abort); resolve(); }, 1000);
    signal.addEventListener('abort', abort, { once: true });
    if (signal.aborted) abort();
  });
}
const selectStyle = 'h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm';

export default function SongInput({ onSongReady, isLoading, setIsLoading }) {
  const [url, setUrl] = useState('');
  const [file, setFile] = useState(null);
  const [seconds, setSeconds] = useState(30);
  const [start, setStart] = useState(0);
  const [instrument, setInstrument] = useState('voice');
  const [tracks, setTracks] = useState([]);
  const [track, setTrack] = useState('');
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const [health, setHealth] = useState(null);
  const [library, setLibrary] = useState(false);
  const controller = useRef(null), job = useRef(''), alive = useRef(true);
  const midi = /\.(mid|midi)$/i.test(file?.name || '');

  useEffect(() => {
    alive.current = true;
    const check = new AbortController();
    fetch('/api/health', { signal: check.signal }).then(readResponse).then(setHealth).catch(() => {});
    return () => { alive.current = false; check.abort(); controller.current?.abort(); };
  }, []);
  useEffect(() => {
    if (!isLoading) return;
    const began = Date.now(); setElapsed(0);
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - began) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [isLoading]);

  const openResult = song => onSongReady(buildAccompaniment(song, 'простая'));
  const poll = async (data, signal) => {
    job.current = data.id; savedJob(data.id);
    while (true) {
      setProgress(data);
      if (data.status === 'ready') { savedJob(''); job.current = ''; openResult(data.song); return; }
      if (data.status === 'error' || data.status === 'cancelled') { savedJob(''); job.current = ''; throw new Error(data.message); }
      await pause(signal);
      data = await fetch(`/api/transcriptions/${data.id}`, { signal }).then(readResponse);
    }
  };
  const submit = async event => {
    event.preventDefault();
    if (isLoading) return;
    setError(''); setProgress(null); setIsLoading(true);
    controller.current?.abort();
    const request = new AbortController(); controller.current = request; job.current = '';
    try {
      if (file && midi) {
        if (file.size > 2 * 1024 * 1024) throw new Error('MIDI-файл должен быть меньше 2 МБ.');
        const body = new FormData(); body.append('file', file);
        if (!tracks.length) {
          const data = await fetch('/api/midi/inspect', { method: 'POST', body, signal: request.signal }).then(readResponse);
          setTracks(data.tracks);
          const preferred = data.tracks.find(item => item.voice) || data.tracks[0];
          setTrack(String(preferred.index));
          if (data.tracks.length > 1) return;
          body.append('track', String(preferred.index));
        } else body.append('track', track);
        const data = await fetch('/api/midi/arrange', { method: 'POST', body, signal: request.signal }).then(readResponse);
        openResult(data.song); return;
      }
      let response;
      if (file) {
        if (file.size > 50 * 1024 * 1024) throw new Error('Аудиофайл должен быть меньше 50 МБ.');
        const body = new FormData(); body.append('file', file);
        body.append('start', String(start)); body.append('seconds', String(seconds)); body.append('instrument', instrument);
        response = await fetch('/api/transcriptions/upload', { method: 'POST', body, signal: request.signal });
      } else response = await fetch('/api/transcriptions', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, start: Number(start), seconds, instrument }), signal: request.signal });
      await poll(await readResponse(response), request.signal);
    } catch (e) {
      if (e.name !== 'AbortError' && alive.current) setError(e.message === 'Failed to fetch' ? 'Нет связи с сервером. Можно проверить результат после восстановления связи.' : e.message);
    } finally { if (alive.current) setIsLoading(false); }
  };
  const resume = async () => {
    const id = savedJob();
    if (!id || isLoading) return;
    setError(''); setIsLoading(true);
    const request = new AbortController(); controller.current = request;
    try {
      const data = await fetch(`/api/transcriptions/${id}`, { signal: request.signal }).then(readResponse);
      await poll(data, request.signal);
    } catch (e) { if (e.name !== 'AbortError' && alive.current) setError(e.message); }
    finally { if (alive.current) setIsLoading(false); }
  };
  const cancel = async () => {
    try { await fetch(`/api/transcriptions/${job.current}`, { method: 'DELETE' }).then(readResponse); }
    catch (e) { setError('Не удалось отменить обработку: ' + e.message); return; }
    controller.current?.abort(); job.current = ''; savedJob(''); setProgress(null); setIsLoading(false);
  };

  if (library) return <div className="space-y-4">
    <Button variant="ghost" disabled={isLoading} onClick={() => setLibrary(false)} className="mx-auto block">← Распознать запись в MuScriptor</Button>
    <LibraryInput onSongReady={onSongReady} isLoading={isLoading} setIsLoading={setIsLoading} />
  </div>;

  return <form onSubmit={submit} className="w-full max-w-2xl mx-auto space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
    <label htmlFor="youtube-url" className="block text-sm font-medium text-slate-700">Ссылка на YouTube</label>
    <Input id="youtube-url" type="url" required={!file} disabled={isLoading || Boolean(file)} value={url}
      onChange={e => setUrl(e.target.value)} placeholder="https://www.youtube.com/watch?v=…" autoComplete="off" />
    <div className="space-y-2">
      <label htmlFor="music-file" className="block text-sm font-medium text-slate-700">Или аудиофайл / MIDI из MuScriptor</label>
      <Input id="music-file" type="file" disabled={isLoading} accept=".mid,.midi,.mp3,.wav,.m4a,.flac,.ogg,.aac,.mp4,.webm"
        onChange={e => { setFile(e.target.files?.[0] || null); setTracks([]); setTrack(''); setError(''); setProgress(null); }} />
      {file && <Button type="button" variant="ghost" disabled={isLoading} onClick={() => {
        setFile(null); setTracks([]); setTrack(''); const input = document.getElementById('music-file'); if (input instanceof HTMLInputElement) input.value = '';
      }}>Убрать файл</Button>}
    </div>
    {midi ? <>
      <p className="text-sm text-slate-500">Откроем готовые ноты и упростим их для баяна. Повторное распознавание не требуется.</p>
      {tracks.length > 1 && <div className="space-y-2">
        <label htmlFor="melody-track" className="block text-sm font-medium text-slate-700">Дорожка мелодии</label>
        <select id="melody-track" className={selectStyle} value={track} onChange={e => setTrack(e.target.value)} disabled={isLoading}>
          {tracks.map(item => <option key={item.index} value={item.index}>{item.name} · {item.notes} нот{item.voice ? ' · вокал' : ''}</option>)}
        </select>
        <p className="text-xs text-slate-500">Выберите вокал или ведущий инструмент для правой руки.</p>
      </div>}
    </> : <>
      <p className="text-sm text-slate-500">MuScriptor распознает запись. Получите одну мелодию правой рукой и простой бас–аккорд левой, B-гриф.</p>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-2">
          <label htmlFor="excerpt-start" className="block text-sm text-slate-700">Начало, секунды</label>
          <Input id="excerpt-start" type="number" min="0" max="570" step="1" required value={start} disabled={isLoading} onChange={e => setStart(Number(e.target.value))} />
        </div>
        <div className="space-y-2">
          <label htmlFor="excerpt-length" className="block text-sm text-slate-700">Длина фрагмента</label>
          <select id="excerpt-length" className={selectStyle} value={seconds} disabled={isLoading} onChange={e => setSeconds(Number(e.target.value))}>
            <option value={30}>30 секунд</option><option value={60}>1 минута</option>
          </select>
        </div>
      </div>
      <label htmlFor="melody-instrument" className="block text-sm text-slate-700">Что играть как мелодию</label>
      <select id="melody-instrument" className={selectStyle} value={instrument} disabled={isLoading} onChange={e => setInstrument(e.target.value)}>
        <option value="voice">Вокал</option><option value="acoustic_piano">Фортепиано</option><option value="flutes">Флейта</option>
        <option value="violin">Скрипка</option><option value="acoustic_guitar">Акустическая гитара</option>
      </select>
      <p className="text-xs text-slate-500">Для песни выберите начало куплета: во вступлении вокальной мелодии может не быть.</p>
      {health?.transcription?.configured === false && <p role="status" className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
        Распознавание на сервере пока не настроено. Можно загрузить MIDI из <a href="https://muscriptor.kyutai.org" target="_blank" rel="noopener noreferrer" className="underline">MuScriptor</a> и сразу играть.
      </p>}
    </>}
    <Button type="submit" disabled={isLoading || (!file && !url.trim())} className="w-full gap-2">
      {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : midi ? <Music className="h-4 w-4" /> : <Youtube className="h-4 w-4" />}
      {isLoading ? 'Обрабатываем…' : midi && tracks.length > 1 ? 'Открыть выбранную мелодию' : midi ? 'Открыть MIDI' : 'Получить мелодию и аккорды'}
    </Button>
    {isLoading && <div role="status" className="space-y-2 text-sm text-slate-600">
      <p>{progress?.message || 'Отправляем запись…'} · {Math.floor(elapsed / 60)}:{String(elapsed % 60).padStart(2, '0')}</p>
      {progress?.total > 0 && <><progress className="h-2 w-full" value={progress.completed} max={progress.total} /><p>Фрагменты: {progress.completed} из {progress.total}</p></>}
      <Button type="button" variant="outline" disabled={!job.current} onClick={cancel}>Отменить</Button>
    </div>}
    {!isLoading && savedJob() && <Button type="button" variant="outline" onClick={resume}>Проверить результат обработки</Button>}
    {error && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    <p className="text-xs text-slate-400">Это упрощённая учебная версия. Ритм и аккомпанемент могут отличаться от оригинала. Переключатель Am доступен в плеере.</p>
    <div className="flex flex-wrap justify-between gap-3 border-t border-slate-100 pt-3 text-xs">
      <a href="https://muscriptor.kyutai.org" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-blue-600 underline">Открыть MuScriptor<ExternalLink className="h-3 w-3" /></a>
      <button type="button" disabled={isLoading} onClick={() => setLibrary(true)} className="text-slate-500 underline">Готовые аранжировки из библиотеки</button>
    </div>
  </form>;
}
