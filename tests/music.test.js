import test from 'node:test';
import assert from 'node:assert/strict';
import { transposeToAm } from '../src/components/bayan/transposeSong.js';
import { B_SYSTEM_ROWS_FROM_BELLOWS } from '../src/components/bayan/bSystem.js';
import { fromMidi, toMidi } from '../src/components/bayan/musicTheory.js';

const fixture = {
  key: 'Dm', tempo: 100,
  right_hand: [{ note: 'D4', time: 0, duration: 1 }, { note: 'F4', time: 1, duration: 1 }, { note: 'C#5', time: 2, duration: .5 }],
  left_hand: [{ note: 'D-bass', time: 0, duration: 1 }, { note: 'Dm-chord', time: 1, duration: 1 }, { note: 'A7-chord', time: 2, duration: 1 }],
  harmony: [{ chord: 'Dm', time: 0, duration: 2 }, { chord: 'A7', time: 2, duration: 1 }],
};
test('Dm -> Am transposes both hands and harmonic-minor leading tone, preserving timing', () => {
  const original = structuredClone(fixture);
  const song = transposeToAm(fixture);
  assert.deepEqual(song.right_hand.map(n => n.note), ['A3', 'C4', 'G#4']);
  assert.deepEqual(song.left_hand.map(n => n.note), ['A-bass', 'Am-chord', 'E7-chord']);
  assert.deepEqual(song.harmony.map(h => h.chord), ['Am', 'E7']);
  assert.deepEqual(song.right_hand.map(({ time, duration }) => [time, duration]), [[0, 1], [1, 1], [2, .5]]);
  assert.deepEqual(fixture, original);
  assert.equal(song.mode_adapted, false);
});
test('major songs explicitly adapt the thirds and accompaniment into A minor', () => {
  const song = transposeToAm({ key: 'C', right_hand: ['C4','E4','A4','B4'].map((note,time) => ({note,time,duration:1})),
    left_hand: [{note:'C-chord'}, {note:'F-chord'}, {note:'G7-chord'}, {note:'Dm-chord'}] });
  assert.deepEqual(song.right_hand.map(n=>n.note), ['A3','C4','F4','G4']);
  assert.deepEqual(song.left_hand.map(n=>n.note), ['Am-chord','Dm-chord','E7-chord','Bdim-chord']);
  assert.equal(song.mode_adapted, true);
});
test('enharmonic keys transpose identically and Am does not drift', () => {
  const flat = transposeToAm({...fixture,key:'Ebm'});
  const sharp = transposeToAm({...fixture,key:'D#m'});
  assert.deepEqual(flat.right_hand, sharp.right_hand);
  assert.deepEqual(flat.left_hand, sharp.left_hand);
});
test('Am stays unchanged and silence is preserved', () => {
  const song = {...fixture, key:'Am', harmony:[{chord:'N',time:0,duration:1}]};
  assert.deepEqual(transposeToAm(song).right_hand, song.right_hand);
  assert.equal(transposeToAm(song).harmony[0].chord,'N');
});
test('B-griff C is in inner row 3; outer row 1 carries D, F, Ab, B', () => {
  assert.deepEqual(B_SYSTEM_ROWS_FROM_BELLOWS[0], [0,3,6,9]);
  assert.deepEqual(B_SYSTEM_ROWS_FROM_BELLOWS[2], [2,5,8,11]);
  assert.equal(new Set(B_SYSTEM_ROWS_FROM_BELLOWS.flat()).size,12);
});
test('MIDI standard middle C is 60 and every keyboard note round trips', () => {
  assert.equal(toMidi('C4'),60);
  for (let midi=36;midi<=96;midi++) assert.equal(toMidi(fromMidi(midi)),midi);
});
