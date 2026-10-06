import ReedVoice from '@/components/bayan/ReedVoice';
import { toMidi, fromMidi, chordInfo } from '@/components/bayan/musicTheory';
let audioCtx = null, output = null;
const voices = new Set();
export function getAudioContext() {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || /** @type {Window & {webkitAudioContext?: typeof AudioContext}} */ (window).webkitAudioContext)();
    output = audioCtx.createDynamicsCompressor();
    output.threshold.value = -16; output.knee.value = 12;
    output.ratio.value = 3; output.attack.value = .006; output.release.value = .15;
    const master = audioCtx.createGain(); master.gain.value = 1.8;
    output.connect(master); master.connect(audioCtx.destination);
  }
  if (audioCtx.state === 'suspended') audioCtx.resume();
  return audioCtx;
}
export function playNote(note, duration=.5, volume=.15, when) {
  const midi = toMidi(note);
  if (midi === null || !(duration>0)) return;
  const ctx = getAudioContext();
  ReedVoice(ctx,output,440*2**((midi-69)/12),duration,volume,when ?? ctx.currentTime,voices);
}
export function playChord(notes,duration=.5,volume=.1,when) {
  notes.forEach(note=>playNote(note,duration,volume/Math.sqrt(notes.length),when));
}
export function parseLeftHandNote(note) {
  if (typeof note !== 'string') return [];
  const bass = note.match(/^([A-G][#b]?)-(bass|counter-?bass)$/);
  if (bass) {
    const midi = toMidi(`${bass[1]}2`) + (bass[2] === 'bass' ? 0 : 4);
    return [fromMidi(midi),fromMidi(midi+12)];
  }
  const info = chordInfo(note.replace(/-chord$/,''));
  if (note.endsWith('-chord') && info) {
    return info.intervals.map(i => { let midi=info.root+i; while(midi>59) midi-=12; return fromMidi(midi); });
  }
  return toMidi(note) === null ? [] : [note];
}
export function stopAll() {
  voices.forEach(voice=>voice.stop()); voices.clear();
}