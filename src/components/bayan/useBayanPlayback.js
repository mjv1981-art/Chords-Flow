import { useEffect, useRef } from 'react';
import { getAudioContext, playNote, playChord, parseLeftHandNote, stopAll } from '@/components/bayan/AudioEngine';
export default function useBayanPlayback(song, playing, tempo, beat, seekVersion, total, setBeat, setPlaying) {
  const position = useRef(beat); position.current = beat;
  useEffect(() => {
    if (!playing || !song) return;
    const ctx = getAudioContext(), startBeat = position.current, seconds = 60/tempo;
    const origin = ctx.currentTime + .04;
    const events = [...(song.right_hand || []).map(n=>({...n,hand:'right'})), ...(song.left_hand || []).map(n=>({...n,hand:'left'}))]
      .filter(n=>n.time+n.duration>startBeat).sort((a,b)=>a.time-b.time);
    let cursor = 0, frame;
    const schedule = () => {
      const horizon = ctx.currentTime + .15;
      while (cursor<events.length) {
        const n = events[cursor], start = Math.max(startBeat,n.time);
        const when = origin + (start-startBeat)*seconds;
        if (when>horizon) break;
        const end = origin+(n.time+n.duration-startBeat)*seconds;
        const actual = Math.max(when,ctx.currentTime);
        if (end>actual) {
          const accent = Math.abs(n.time-Math.round(n.time))<.001 ? 1 : .88;
          if (n.hand==='right') playNote(n.note,end-actual,(n.velocity || .12)*accent,actual);
          else playChord(parseLeftHandNote(n.note),end-actual,(n.velocity || .085)*accent,actual);
        }
        cursor++;
      }
    };
    const draw = () => {
      const next = Math.min(total,startBeat+Math.max(0,ctx.currentTime-origin)/seconds);
      setBeat(next);
      if (next>=total) { setPlaying(false); return; }
      frame = requestAnimationFrame(draw);
    };
    schedule(); frame = requestAnimationFrame(draw);
    const timer = setInterval(schedule,25);
    return () => { clearInterval(timer); cancelAnimationFrame(frame); stopAll(); };
  },[song,playing,tempo,seekVersion,total,setBeat,setPlaying]);
}