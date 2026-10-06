export const PITCHES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
export function toMidi(note) {
  const m = typeof note === 'string' && note.match(/^([A-G])([#b]?)(-?\d+)$/);
  if (!m) return null;
  return (Number(m[3]) + 1) * 12 + {C:0,D:2,E:4,F:5,G:7,A:9,B:11}[m[1]] + (m[2] === '#' ? 1 : m[2] === 'b' ? -1 : 0);
}
export const fromMidi = n => `${PITCHES[((n % 12) + 12) % 12]}${Math.floor(n / 12) - 1}`;
export function chordInfo(symbol) {
  const m = symbol?.match(/^([A-G][#b]?)(maj|M|m|7|dim|°)?$/);
  if (!m) return null;
  const root = toMidi(`${m[1]}3`);
  return {root, name:m[1], intervals: m[2] === 'm' ? [0,3,7] : m[2] === '7' ? [0,4,7,10] : ['dim','°'].includes(m[2]) ? [0,3,6,9] : [0,4,7]};
}