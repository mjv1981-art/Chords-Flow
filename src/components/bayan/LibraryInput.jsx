import { useEffect, useRef, useState } from 'react';
import { ExternalLink, Loader2, Youtube } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import buildAccompaniment from './buildAccompaniment';

async function readResponse(response) {
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'Сервис недоступен. Попробуйте ещё раз.');
  return data;
}

export default function LibraryInput({ onSongReady, isLoading, setIsLoading }) {
  const [url, setUrl] = useState('');
  const [query, setQuery] = useState('');
  const [identified, setIdentified] = useState(null);
  const [error, setError] = useState('');
  const request = useRef(null);
  useEffect(() => () => request.current?.abort(), []);

  const identify = async event => {
    event.preventDefault();
    if (isLoading) return;
    setError(''); setIsLoading(true);
    request.current?.abort();
    const controller = new AbortController(); request.current = controller;
    try {
      const result = await fetch('/api/song-lookup', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, query }), signal: controller.signal,
      }).then(readResponse);
      setIdentified(result);
      setQuery(result.query);
    } catch (e) {
      if (e.name !== 'AbortError') setError(e.message === 'Failed to fetch' ? 'Нет связи с сервером.' : e.message);
    } finally { setIsLoading(false); }
  };

  const openSong = async candidate => {
    if (isLoading) return;
    setError(''); setIsLoading(true);
    request.current?.abort();
    const controller = new AbortController(); request.current = controller;
    try {
      const result = await fetch('/api/library-song', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, song_id: candidate.id }), signal: controller.signal,
      }).then(readResponse);
      onSongReady(buildAccompaniment(result.song, 'простая'));
    } catch (e) {
      if (e.name !== 'AbortError') setError(e.message);
    } finally { setIsLoading(false); }
  };

  return <form onSubmit={identify} className="w-full max-w-2xl mx-auto space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
    <label htmlFor="youtube-url" className="block text-sm font-medium text-slate-700">Ссылка на YouTube</label>
    <Input id="youtube-url" type="url" required value={url} onChange={e => {
      setUrl(e.target.value); setQuery(''); setIdentified(null); setError('');
    }} disabled={isLoading} placeholder="https://www.youtube.com/watch?v=…" autoComplete="off" />
    <p className="text-sm text-slate-500">Найдём название песни и готовую аранжировку: одна мелодия и простой бас–аккорд для баяна, B-гриф.</p>
    {identified && <>
      {identified.video.metadata_available ? <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
        <p>Название видео: <strong>{identified.video.title}</strong></p>
        {identified.video.author && <p className="mt-1 text-xs">Канал: {identified.video.author}</p>}
      </div> : identified.manual_name ? <p className="text-sm text-slate-500">Ищем по названию, указанному вами.</p> :
        <p role="status" className="text-sm text-amber-700">YouTube не вернул название. Укажите песню и исполнителя ниже.</p>}
      <label htmlFor="song-name" className="block text-sm font-medium text-slate-700">Песня и исполнитель</label>
      <Input id="song-name" value={query} onChange={e => setQuery(e.target.value)} disabled={isLoading}
        placeholder="Nightwish — Sleeping Sun" autoComplete="off" />
    </>}
    <Button type="submit" disabled={isLoading || !url.trim()} className="w-full gap-2">
      {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Youtube className="h-4 w-4" />}
      {isLoading ? 'Ищем…' : identified ? 'Найти аранжировку' : 'Определить песню'}
    </Button>
    {identified?.matches?.length > 0 && <div className="space-y-3">
      <p className="text-sm font-medium text-slate-700">Это та песня? Подтвердите перед открытием:</p>
      {identified.matches.map(candidate => <div key={candidate.id} className="space-y-2 rounded-xl border border-slate-200 p-4">
        <p className="font-semibold text-slate-800">{candidate.artist} — {candidate.title}</p>
        <p className="text-xs text-slate-500">{candidate.description}</p>
        <a className="inline-flex items-center gap-1 text-xs text-blue-600 underline" href={candidate.source_url} target="_blank" rel="noopener noreferrer">
          Нотный источник: {candidate.source_name}<ExternalLink className="h-3 w-3" />
        </a>
        <Button type="button" disabled={isLoading} className="w-full" onClick={() => openSong(candidate)}>Да, открыть {candidate.title}</Button>
      </div>)}
      <p className="text-xs text-slate-500">Тональность и темп аранжировки могут отличаться от видео. В плеере доступен переключатель Am.</p>
    </div>}
    {identified && !identified.needs_name && identified.matches.length === 0 && <p role="status" className="text-sm text-slate-600">
      Для этой песни готовой аранжировки пока нет. В библиотеке: {identified.library_count}. Можно поискать источник по ссылкам ниже.
    </p>}
    {identified?.search_links?.length > 0 && <div className="flex flex-wrap gap-3 text-sm">
      {identified.search_links.map(link => <a key={link.label} href={link.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-blue-600 underline">
        Найти {link.label.toLowerCase()}<ExternalLink className="h-3 w-3" />
      </a>)}
    </div>}
    {error && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    <p className="text-xs text-slate-400">Играем по готовым нотным источникам. Аудио не анализируется; ключ AI API не нужен. Новые песни добавляются в библиотеку после проверки аранжировки.</p>
  </form>;
}
