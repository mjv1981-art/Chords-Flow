"""Deterministic beginner arrangement from an explicitly selected MIDI voice."""
from collections import defaultdict
import hashlib
import math
from pathlib import Path

import mido

PITCHES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]


def read_notes(midi):
    notes, metadata = [], []
    for index, track in enumerate(midi.tracks):
        clock, active = 0, defaultdict(list)
        for message in track:
            clock += message.time
            beat = clock / midi.ticks_per_beat
            if message.is_meta:
                metadata.append((beat, message))
                continue
            if message.type not in {'note_on', 'note_off'} or message.channel == 9:
                continue
            key = (message.channel, message.note)
            if message.type == 'note_on' and message.velocity:
                active[key].append((beat, message.velocity))
            elif active[key]:
                start, velocity = active[key].pop(0)
                if beat > start:
                    notes.append({'track': index, 'midi': message.note, 'start': start,
                                  'end': beat, 'velocity': velocity})
    return notes, sorted(metadata, key=lambda item: item[0])


def infer_key(notes):
    weights = [0.0] * 12
    for note in notes:
        weights[note['midi'] % 12] += note['end'] - note['start']
    mean = sum(weights) / 12
    centered = [weight - mean for weight in weights]
    def correlation(root, profile):
        average = sum(profile) / 12
        shifted = [profile[(pitch - root) % 12] - average for pitch in range(12)]
        scale = math.sqrt(sum(v*v for v in shifted) * sum(v*v for v in centered))
        return sum(a*b for a,b in zip(centered, shifted)) / scale if scale else 0
    root, mode = max(((root, mode) for root in range(12) for mode in ['', 'm']),
                     key=lambda item: correlation(item[0], MINOR if item[1] else MAJOR))
    return PITCHES[root] + mode


def convert_midi(path, *, title, artist, melody_track, harmony_tracks, arranger=''):
    path = Path(path)
    midi = mido.MidiFile(path)
    if midi.type == 2:
        raise ValueError('Independent MIDI sequences cannot be combined into one song.')
    if melody_track in harmony_tracks or not harmony_tracks:
        raise ValueError('Select separate melody and accompaniment tracks.')
    notes, metadata = read_notes(midi)
    voice = [note for note in notes if note['track'] == melody_track]
    accompaniment = [note for note in notes if note['track'] in harmony_tracks]
    if not voice or not accompaniment:
        raise ValueError('The chosen tracks must contain melody and accompaniment notes.')
    start = math.floor(min(note['start'] for note in voice) / 4) * 4
    meter = next((f'{msg.numerator}/{msg.denominator}' for _,msg in metadata if msg.type == 'time_signature'), '4/4')
    if meter != '4/4':
        raise ValueError('This starter importer supports 4/4 arrangements only.')
    tempo = next((msg.tempo for beat,msg in reversed(metadata) if msg.type == 'set_tempo' and beat <= start), 500000)
    bpm = round(mido.tempo2bpm(tempo))
    if not 40 <= bpm <= 240:
        raise ValueError('Tempo is outside the player practice range.')
    groups = defaultdict(list)
    for note in voice:
        if note['end'] - note['start'] < .25:
            continue  # Remove short ornaments.
        groups[max(0, round((note['start'] - start) * 2) / 2)].append(note)
    right = []
    for beat, simultaneous in sorted(groups.items()):
        note = max(simultaneous, key=lambda note: note['midi'])
        pitch = note['midi']
        while pitch < 48:
            pitch += 12
        while pitch > 84:
            pitch -= 12
        end = max(beat + .5, round((note['end'] - start) * 2) / 2)
        if right and right[-1]['time'] + right[-1]['duration'] > beat:
            right[-1]['duration'] = beat - right[-1]['time']
        right.append({'note': f'{PITCHES[pitch % 12]}{pitch // 12 - 1}', 'time': beat, 'duration': end - beat})
    if not right:
        raise ValueError('No melody survived simplification.')
    end = max(note['time'] + note['duration'] for note in right)
    signature = next((msg.key for _,msg in metadata if msg.type == 'key_signature'), None)
    key = signature or infer_key(voice + accompaniment)
    tonic = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[key[0]]
    tonic += 1 if '#' in key else -1 if 'b' in key else 0
    scale = {(tonic + interval) % 12 for interval in ([0,2,3,5,7,8,10] if key.endswith('m') else [0,2,4,5,7,9,11])}
    candidates = [(root, suffix, {(root + interval) % 12 for interval in intervals})
                  for root in range(12) for suffix,intervals in [('', [0,4,7]), ('m',[0,3,7]), ('dim',[0,3,6])]]
    harmony = []
    for beat in range(0, math.ceil(end), 4):
        finish = min(end, beat + 4)
        weights, bass = [0.0]*12, [0.0]*12
        for note in accompaniment:
            overlap = min(note['end'] - start, finish) - max(note['start'] - start, beat)
            if overlap > 0:
                weights[note['midi'] % 12] += overlap
                if note['midi'] < 48:
                    bass[note['midi'] % 12] += overlap
        total = sum(weights)
        if not total:
            chord = 'N'
        else:
            root, suffix, _ = max(candidates, key=lambda candidate:
                sum(weights[pitch] for pitch in candidate[2]) + .35*bass[candidate[0]] +
                .02*total*len(candidate[2] & scale))
            chord = PITCHES[root] + suffix
        if harmony and harmony[-1]['chord'] == chord:
            harmony[-1]['duration'] += finish - beat
        else:
            harmony.append({'chord': chord, 'time': beat, 'duration': finish - beat})
    return {'title': title, 'composer': artist, 'key': key, 'tempo': bpm, 'time_signature': '4/4',
            'right_hand': right, 'harmony': harmony, 'difficulty': 'простая',
            'arranger': arranger, 'source_midi_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'source_melody_track': melody_track, 'source_harmony_tracks': harmony_tracks,
            'source_start_beat': start, 'key_estimated': signature is None}
