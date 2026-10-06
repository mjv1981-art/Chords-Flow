import { chordInfo, fromMidi, toMidi } from '@/components/bayan/musicTheory';
export default function buildAccompaniment(score, difficulty='средняя') {
  const right_hand = (score.right_hand || []).map(n=>({...n}));
  if (!right_hand.length || right_hand.some(n=>toMidi(n.note)===null || !Number.isFinite(n.time) || n.time<0 || !Number.isFinite(n.duration) || n.duration<=0)) throw new Error('Нотная запись неполная или содержит некорректные ноты. Загрузите более чёткий источник.');
  if (!(score.tempo>=40 && score.tempo<=300)) throw new Error('Не удалось определить корректный темп.');
  const [count,unit] = (score.time_signature || '').split('/').map(Number);
  if (!(count>0 && [2,4,8,16].includes(unit))) throw new Error('Не удалось определить размер.');
  const length = Math.max(...right_hand.map(n=>n.time+n.duration));
  const harmony = [...(score.harmony || [])].sort((a,b)=>a.time-b.time);
  let covered = 0;
  for (const h of harmony) {
    if ((h.chord !== 'N' && !chordInfo(h.chord)) || !Number.isFinite(h.time) || !Number.isFinite(h.duration) || h.duration<=0 || Math.abs(h.time-covered)>.01) throw new Error('Не удалось получить непрерывную гармонию. Уточните нотный источник.');
    covered = h.time+h.duration;
  }
  if (covered<length-.01) throw new Error('Гармония не охватывает всю мелодию. Попробуйте более чёткие ноты.');
  const left_hand = [], pulse = 4/unit;
  for (let time=0; time<length-.001; time+=pulse) {
    const h = harmony.find(h=>time>=h.time-.001 && time<h.time+h.duration-.001);
    if (!h || h.chord === 'N') continue;
    const info = chordInfo(h.chord), slot = Math.round(time/pulse), within = slot%count;
    const bass = count%3===0 ? within%3===0 : within%2===0;
    const fifth = difficulty!=='простая' && Math.floor(slot/(count%3===0 ? 3 : 2))%2===1;
    const root = fromMidi(info.root+(fifth ? 7 : 0)).replace(/-?\d+$/,'');
    const duration = Math.min(pulse*(bass ? .82 : .55),length-time,h.time+h.duration-time);
    left_hand.push({note:bass ? `${root}-bass` : `${h.chord}-chord`,time,duration});
  }
  if (difficulty==='сложная') {
    score.right_hand.forEach(n=> {
      const h=harmony.find(h=>n.time>=h.time && n.time<h.time+h.duration);
      if (!h || n.duration<.5) return;
      const info=chordInfo(h.chord), midi=toMidi(n.note);
      if (!info.intervals.some(i=>(info.root+i)%12===midi%12)) return;
      const interval=[3,4,8,9].find(gap=>info.intervals.some(i=>(info.root+i)%12===(midi-gap)%12));
      if (interval) right_hand.push({note:fromMidi(midi-interval),time:n.time,duration:n.duration,velocity:.065});
    });
  }
  return {...score,difficulty,right_hand:right_hand.sort((a,b)=>a.time-b.time),left_hand};
}
