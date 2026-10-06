import React from 'react';
import { ExternalLink } from 'lucide-react';
export default function KaraokeLyrics({song,beat,onSeek}) {
  const lines=song?.lyrics || [];
  const index=lines.findIndex(l=>beat>=l.time && beat<l.time+l.duration);
  const current=lines[index],next=index>=0?lines[index+1]:lines.find(l=>l.time>beat);
  const previous=index>0?lines[index-1]:null;
  const progress=current?Math.min(100,Math.max(0,(beat-current.time)/current.duration*100)):0;
  return <section className="mt-3 shrink-0 rounded-xl border border-border bg-card p-3 text-center" aria-label="Текст песни">
    <div className="flex flex-wrap justify-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
      <span>{song?.arrangement_kind==='chords'?'Аккордовый эскиз · не мелодия песни':'Баян · мелодия + бас–аккорд · без вокала'}</span>
      {song?.source_url?.startsWith('https://') && <a className="inline-flex items-center gap-1 underline" href={song.source_url} target="_blank" rel="noopener noreferrer">YouTube <ExternalLink className="h-3 w-3" /></a>}
      {song?.lyrics_source?.startsWith('https://') && <a className="inline-flex items-center gap-1 underline" href={song.lyrics_source} target="_blank" rel="noopener noreferrer">Источник текста <ExternalLink className="h-3 w-3" /></a>}
    </div>
    {lines.length ? <>
      <p className="mt-2 min-h-5 truncate text-sm text-muted-foreground">{previous?.text || '\u00a0'}</p>
      <p className="py-2 text-xl font-semibold text-primary sm:text-2xl">{current?.text || (next ? 'Проигрыш' : 'Конец песни')}</p>
      <div className="h-1 overflow-hidden rounded-full bg-muted"><div className="h-full bg-primary" style={{width:`${progress}%`}} /></div>
      <button type="button" disabled={!next} onClick={()=>next && onSeek(next.time)} className="mt-2 min-h-6 max-w-full truncate text-sm text-muted-foreground hover:text-foreground disabled:pointer-events-none" title="Перейти к следующей строке">{next?.text || '\u00a0'}</button>
      <p className="mt-1 text-xs text-muted-foreground">{song.lyrics_notice || 'Строки из нотного источника; распознавание может ошибаться.'}</p>
    </> : <p className="mt-3 text-sm text-muted-foreground">{song?.lyrics_notice || 'Подстрочник для этой версии не найден — воспроизводится инструментальная партия.'}</p>}
  </section>;
}