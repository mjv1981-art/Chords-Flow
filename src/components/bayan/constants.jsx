// Right-hand B-griff rows are defined in bSystem.js.
export const NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
export const STRADELLA_ORDER = ['Eb', 'Bb', 'F', 'C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#', 'G#'];

export const NOTE_COLORS = {
  'C': '#FF6B6B',
  'C#': '#FF8E53',
  'D': '#FFA726',
  'D#': '#FFCA28',
  'E': '#66BB6A',
  'F': '#26A69A',
  'F#': '#29B6F6',
  'G': '#42A5F5',
  'G#': '#5C6BC0',
  'A': '#7E57C2',
  'A#': '#AB47BC',
  'B': '#EC407A'
};

// Преобразование Bb -> A# для унификации
export function normalizeNoteName(name) {
  const flats = { 'Db': 'C#', 'Eb': 'D#', 'Fb': 'E', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#', 'Cb': 'B' };
  return flats[name] || name;
}
