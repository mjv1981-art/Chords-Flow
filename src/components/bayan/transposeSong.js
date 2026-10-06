import { fromMidi, toMidi } from './musicTheory.js';

const pitchClass = n => ((n % 12) + 12) % 12;
const MAJOR_TO_MINOR = [0, 1, 2, 3, 3, 5, 6, 7, 8, 8, 10, 10];
const MINOR_CHORDS = { 0: 'm', 2: 'dim', 4: '', 5: 'm', 7: 'm', 9: '', 11: '' };

// Major -> Am is explicitly a mode adaptation; minor -> Am is a transposition.
export function transposeToAm(song) {
  const match = song.key?.match(/^([A-G][#b]?)(m)?$/);
  if (!match) throw new Error('Тональность песни не определена.');
  const tonic = pitchClass(toMidi(`${match[1]}4`));
  let shift = 9 - tonic;
  if (shift > 6) shift -= 12;
  if (shift < -6) shift += 12;
  const major = !match[2];
  const transformMidi = midi => {
    const degree = pitchClass(midi - tonic);
    return midi + shift + (major ? MAJOR_TO_MINOR[degree] - degree : 0);
  };
  const transposeLeft = note => {
    if (note === 'N-chord') return note;
    const parsed = note.match(/^([A-G][#b]?)(m|7|dim|°)?-(bass|counter-bass|chord)$/);
    if (!parsed) throw new Error(`Неизвестная кнопка: ${note}`);
    const root = toMidi(`${parsed[1]}3`);
    const degree = pitchClass(root - tonic);
    let suffix = parsed[2] || '';
    if (major && parsed[3] === 'chord' && degree in MINOR_CHORDS) {
      suffix = degree === 7 && suffix === '7' ? '7' : MINOR_CHORDS[degree];
    }
    return `${fromMidi(transformMidi(root)).replace(/-?\d+$/, '')}${suffix}-${parsed[3]}`;
  };
  return { ...song, key: 'Am', original_key: song.key, mode_adapted: major,
    right_hand: song.right_hand.map(n => ({ ...n, note: fromMidi(transformMidi(toMidi(n.note))) })),
    left_hand: song.left_hand.map(n => ({ ...n, note: transposeLeft(n.note) })),
    harmony: song.harmony?.map(h => ({ ...h, chord: transposeLeft(`${h.chord}-chord`).replace(/-chord$/, '') })),
  };
}
