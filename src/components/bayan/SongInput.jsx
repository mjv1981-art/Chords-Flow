import { useEffect, useRef, useState } from 'react';
import { Loader2, Youtube } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import buildAccompaniment from './buildAccompaniment';

async function readResponse(response) {
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'Сервис недоступен. Попробуйте ещё раз.');
  return data;
}
export default function SongInput({ onSongReady, isLoading, setIsLoading }) {
  const [url, setUrl] = useState('');
  const [error, setError] = useState('');
  const [progress, setProgress] = useState('');
  const [configured, setConfigured] = useState(null);
  const request = useRef(null);
  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/health', { signal: controller.signal }).then(readResponse)
      .then(data => setConfigured(data.transcription_configured && data.ffmpeg_available))
      .catch(() => {});
    return () => { controller.abort(); request.current?.abort(); };
  }, []);
  const submit = async event => {
    event.preventDefault();
    if (isLoading) return;
    setError(''); setProgress('Открываем видео через Gemini…'); setIsLoading(true);
    const controller = new AbortController(); request.current = controller;
    try {
      const created = await fetch('/api/transcriptions', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }), signal: controller.signal,
      }).then(readResponse);
      for (;;) {
        await new Promise(resolve => setTimeout(resolve, 1500));
        const job = await fetch(`/api/transcriptions/${created.id}`, { signal: controller.signal }).then(readResponse);
        if (job.status === 'failed') throw new Error(job.error);
        if (job.status === 'complete') {
          onSongReady(buildAccompaniment(job.song, 'простая'));
          break;
        }
        setProgress(job.progress || 'Распознаём мелодию и аккорды…');
      }
    } catch (e) {
      if (e.name !== 'AbortError') setError(e.message === 'Failed to fetch' ? 'Нет связи с сервером. Проверьте, что он запущен.' : e.message);
    } finally { setIsLoading(false); setProgress(''); }
  };
  return <form onSubmit={submit} className="w-full max-w-2xl mx-auto space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
    <label htmlFor="youtube-url" className="block text-sm font-medium text-slate-700">Ссылка на YouTube</label>
    <Input id="youtube-url" type="url" required value={url} onChange={e => setUrl(e.target.value)} disabled={isLoading}
      placeholder="https://www.youtube.com/watch?v=…" autoComplete="off" />
    <p className="text-sm text-slate-500">Одна мелодия правой рукой и простой бас–аккорд левой. Русский баян, B-гриф. Видео до 10 минут.</p>
    <Button type="submit" disabled={isLoading || !url.trim()} className="w-full gap-2">
      {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Youtube className="h-4 w-4" />}
      {isLoading ? 'Распознаём…' : 'Получить мелодию и аккорды'}
    </Button>
    {progress && <p role="status" className="text-sm text-slate-600">{progress}</p>}
    {configured === false && <p className="text-sm text-amber-700">Распознавание пока не настроено на сервере. Нужен ключ Gemini API.</p>}
    {error && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    <p className="text-xs text-slate-400">Gemini распознаёт музыку по ссылке на видео. Это упрощённая учебная версия; сложные записи могут распознаваться с ошибками.</p>
  </form>;
}
