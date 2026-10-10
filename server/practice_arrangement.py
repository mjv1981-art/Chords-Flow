"""Turn timed, transcribed notes into one playable beginner bayan voice."""
import bisect
import io
import math
from collections import defaultdict

import mido

from .midi_arrangement import PITCHES, infer_key
from .transcription import TranscriptionError

MAX_MIDI_BYTES = 2 * 1024 * 1024
MAX_NOTES = 50000


def midi_material(data):
    if len(data) > MAX_MIDI_BYTES or not data.startswith(b'MThd'):
        raise TranscriptionError('Выберите MIDI-файл размером до 2 МБ.')
    try:
        midi = mido.MidiFile(file=io.BytesIO(data))
        if midi.type == 2 or len(midi.tracks) > 128:
            raise ValueError()
        notes, tempos, signatures, key = [], [(0, 500000)], [], None
        tracks = []
        for index, track in enumerate(midi.tracks):
            tick, active, name, programs = 0, defaultdict(list), '', {}
            for message in track:
                tick += message.time
                if tick > midi.ticks_per_beat * 30000:
                    raise ValueError()
                if message.type == 'track_name':
                    name = message.name[:100]
                elif message.type == 'set_tempo':
                    tempos.append((tick, message.tempo))
                elif message.type == 'time_signature':
                    signatures.append((tick, message.numerator, message.denominator))
                elif message.type == 'key_signature' and key is None:
                    key = message.key
                elif message.type == 'program_change':
                    programs[message.channel] = message.program
                elif message.type in {'note_on', 'note_off'} and message.channel != 9:
                    pair = (message.channel, message.note)
                    if message.type == 'note_on' and message.velocity:
                        active[pair].append((tick, message.velocity, programs.get(message.channel, 0)))
                    elif active[pair]:
                        start, velocity, program = active[pair].pop(0)
                        if tick > start:
                            notes.append(dict(track=index, midi=message.note, start=start, end=tick,
                                              velocity=velocity, program=program))
                            if len(notes) > MAX_NOTES:
                                raise ValueError()
            count = sum(note['track'] == index for note in notes)
            if count:
                tracks.append(dict(index=index, name=name or f'Дорожка {index + 1}', notes=count,
                                   voice=any(note['track'] == index and 52 <= note['program'] <= 54 for note in notes)))
        if not notes:
            raise ValueError()
        changes = dict(sorted(tempos, key=lambda item: item[0]))
        ticks, seconds, speeds, current = [], [], [], 0.0
        for tick, tempo in changes.items():
            if ticks:
                current += mido.tick2second(tick - ticks[-1], midi.ticks_per_beat, speeds[-1])
            ticks.append(tick); seconds.append(current); speeds.append(tempo)
        def seconds_at(tick):
            index = bisect.bisect_right(ticks, tick) - 1
            return seconds[index] + mido.tick2second(tick - ticks[index], midi.ticks_per_beat, speeds[index])
        for note in notes:
            note['start'], note['end'] = seconds_at(note['start']), seconds_at(note['end'])
        tempo_index = bisect.bisect_right(seconds, min(n['start'] for n in notes)) - 1
        tempo = round(mido.tempo2bpm(speeds[tempo_index]))
        numerator, denominator = (signatures[0][1:] if signatures else (4, 4))
        return dict(notes=notes, tracks=tracks, tempo=tempo, meter=f'{numerator}/{denominator}',
                    key=key, tempo_changes=len(changes) > 1)
    except (ValueError, OSError, EOFError, IndexError, KeyError, TypeError, ZeroDivisionError):
        raise TranscriptionError('Не удалось прочитать MIDI. Экспортируйте стандартный MIDI из MuScriptor.') from None


def simple_arrangement(notes, *, melody, title, tempo=120, meter='4/4', key=None,
                       source_url='', origin='muscriptor', tempo_estimated=False):
    valid = []
    for note in notes:
        start, end, pitch = note.get('start'), note.get('end'), note.get('midi')
        if (type(pitch) is not int or not 0 <= pitch <= 127 or
                not isinstance(start, (float, int)) or not isinstance(end, (float, int)) or
                not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start):
            raise TranscriptionError('Распознавание вернуло некорректные времена или высоты нот.')
        valid.append(note)
    voice = [note for note in valid if melody(note)]
    if not voice:
        raise TranscriptionError('Мелодия не найдена. Выберите фрагмент с пением или другой инструмент мелодии.')
    if len(valid) > MAX_NOTES:
        raise TranscriptionError('Слишком много нот. Выберите более короткий фрагмент.')
    tempo = float(tempo)
    if not math.isfinite(tempo) or not 40 <= tempo <= 240:
        tempo, tempo_estimated = 120, True
    # A practice grid preserves relative timings. It flattens tempo changes.
    if meter not in {'3/4', '4/4', '6/8'}:
        meter = '4/4'
    numerator, denominator = map(int, meter.split('/'))
    bar = numerator * 4 / denominator
    beat_seconds = 60 / tempo
    start = math.floor(min(note['start'] for note in voice) / beat_seconds / bar) * bar * beat_seconds
    groups = defaultdict(list)
    for note in voice:
        if note['end'] - note['start'] < beat_seconds * .2:
            continue
        beat = max(0, round((note['start'] - start) / beat_seconds * 2) / 2)
        groups[beat].append(note)
    right = []
    for beat, simultaneous in sorted(groups.items()):
        # Favor sustained tones over ornaments; only one note at each onset.
        note = max(simultaneous, key=lambda note:(note['end'] - note['start'], note['midi']))
        pitch = note['midi']
        while pitch < 48: pitch += 12
        while pitch > 84: pitch -= 12
        finish = max(beat + .5, round((note['end'] - start) / beat_seconds * 2) / 2)
        if right and right[-1]['time'] + right[-1]['duration'] > beat:
            right[-1]['duration'] = beat - right[-1]['time']
        right.append(dict(note=f'{PITCHES[pitch % 12]}{pitch // 12 - 1}', time=beat, duration=finish - beat))
    if not right:
        raise TranscriptionError('Нет устойчивой мелодии. Выберите другой фрагмент записи.')
    length = max(note['time'] + note['duration'] for note in right)
    accompaniment = [note for note in valid if not melody(note) and note.get('instrument') != 'drums']
    arranged_harmony = not bool(accompaniment)
    harmony_notes = accompaniment or voice
    key = key or infer_key(voice + accompaniment)
    tonic = {'C':0, 'D':2, 'E':4, 'F':5, 'G':7, 'A':9, 'B':11}[key[0]]
    tonic += 1 if '#' in key else -1 if 'b' in key else 0
    scale = {(tonic + interval) % 12 for interval in ([0,2,3,5,7,8,10] if key.endswith('m') else [0,2,4,5,7,9,11])}
    candidates = [(root, suffix, {(root + interval) % 12 for interval in intervals})
                  for root in range(12) for suffix, intervals in [('',[0,4,7]),('m',[0,3,7]),('dim',[0,3,6])]]
    harmony = []
    beat = 0.0
    while beat < length:
        finish = min(length, beat + bar)
        weights, bass = [0.0] * 12, [0.0] * 12
        for note in harmony_notes:
            overlap = min((note['end'] - start) / beat_seconds, finish) - max((note['start'] - start) / beat_seconds, beat)
            if overlap > 0:
                weights[note['midi'] % 12] += overlap
                if note['midi'] < 48: bass[note['midi'] % 12] += overlap
        total = sum(weights)
        if total:
            root, suffix, _ = max(candidates, key=lambda candidate:
                sum(weights[pitch] for pitch in candidate[2]) + .35 * bass[candidate[0]] +
                (.12 if arranged_harmony else .02) * total * len(candidate[2] & scale))
            chord = PITCHES[root] + suffix
        else:
            chord = 'N'
        if harmony and harmony[-1]['chord'] == chord:
            harmony[-1]['duration'] += finish - beat
        else:
            harmony.append(dict(chord=chord, time=beat, duration=finish - beat))
        beat = finish
    notice = 'Одна мелодия и упрощённый бас–аккорд.'
    if arranged_harmony: notice += ' Аккомпанемент подобран по мелодии; исходных аккордов в записи может не быть.'
    if tempo_estimated: notice += ' Темп приблизительный; его можно изменить в плеере.'
    return dict(title=title[:200], composer='', key=key, tempo=round(tempo, 2), time_signature=meter,
                right_hand=right, harmony=harmony, difficulty='простая', arrangement_kind='melody',
                source_url=source_url, transcription_engine=origin, harmony_arranged=arranged_harmony,
                tempo_estimated=tempo_estimated, source_start_seconds=round(start, 3), lyrics_notice=notice)


def arrange_midi(data, track, title):
    material = midi_material(data)
    if track not in {entry['index'] for entry in material['tracks']}:
        raise TranscriptionError('Выберите дорожку, содержащую мелодию.')
    return simple_arrangement(material['notes'], melody=lambda note:note['track'] == track, title=title,
                              tempo=material['tempo'], meter=material['meter'], key=material['key'],
                              origin='midi', tempo_estimated=material['tempo_changes'])
