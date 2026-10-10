"""Isolated MuScriptor process. Stdout contains only our JSON progress protocol."""
import contextlib
import json
import os
from pathlib import Path
import socket
import sys


def run(config, emit):
    import numpy as np
    import soundfile as sf
    import torch
    from muscriptor.events import NoteEndEvent, ProgressEvent
    from muscriptor.transcription_model import TranscriptionModel

    torch.set_num_threads(max(1, min(4, int(os.environ.get('MUSCRIPTOR_THREADS', '2')))))
    emit(dict(type='progress', stage='loading', message='Загружаем модель MuScriptor…'))
    model = TranscriptionModel.load_model(weights_path=config['model'], device='cpu')
    emit(dict(type='progress', stage='recognizing', message='Распознаём ноты…', completed=0, total=0))
    events, notes = [], []
    for event in model.transcribe(config['audio'], batch_size=1, prelude_forcing=True):
        events.append(event)
        if isinstance(event, ProgressEvent):
            emit(dict(type='progress', stage='recognizing', message='Распознаём ноты…',
                      completed=event.completed, total=event.total))
        elif isinstance(event, NoteEndEvent) and event.start_event.instrument != 'drums':
            start = event.start_event
            if event.end_time > start.start_time:
                notes.append(dict(midi=start.pitch, start=start.start_time, end=event.end_time,
                                  instrument=start.instrument))
    emit(dict(type='progress', stage='arranging', message='Определяем ритм и упрощаем аккомпанемент…'))
    grid = None
    socket.setdefaulttimeout(15)
    try:
        grid = model.detect_beat_grid_for(config['audio'], mode='best-effort')
    except Exception:
        # Optional Beat This weights/network failures must not discard notes.
        pass
    # A lightweight fallback needs no second model. Ambiguous or rubato
    # recordings use an explicitly approximate practice grid.
    audio, sample_rate = sf.read(config['audio'], dtype='float32')
    if audio.ndim > 1: audio = audio.mean(axis=1)
    tempo = 120.0
    if grid is None and len(audio) >= 4 * sample_rate:
        frames = np.lib.stride_tricks.sliding_window_view(audio, 1024)[::256]
        spectrum = np.abs(np.fft.rfft(frames * np.hanning(1024)))
        flux = np.maximum(np.diff(spectrum, axis=0), 0).sum(axis=1)
        flux -= flux.mean()
        correlation = np.correlate(flux, flux, mode='full')[len(flux)-1:]
        fps = sample_rate / 256
        lower, upper = int(fps * 60 / 180), int(fps * 60 / 60)
        if len(correlation) > upper and correlation[0] > 0:
            scores = correlation[lower:upper+1]
            lag = int(scores.argmax()) + lower
            if correlation[lag] / correlation[0] > .12:
                tempo = float(60 * fps / lag)
    meter = '4/4'
    if grid is not None:
        tempo = grid.bpm
        if grid.beats_per_bar in {3, 4}: meter = f'{grid.beats_per_bar}/4'
    result = dict(notes=notes, tempo=tempo, tempo_estimated=grid is None, meter=meter,
                  meter_estimated=grid is None or grid.beats_per_bar not in {3, 4})
    Path(config['result']).write_text(json.dumps(result, allow_nan=False))
    Path(config['midi']).write_bytes(model.events_to_midi_bytes(iter(events)))
    emit(dict(type='done'))


def main():
    channel = sys.stdout
    def emit(event):
        channel.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + '\n')
        channel.flush()
    try:
        config = json.loads(Path(sys.argv[1]).read_text())
        # Third-party informational prints never corrupt the JSON channel.
        with contextlib.redirect_stdout(sys.stderr):
            run(config, emit)
    except Exception as error:
        name = type(error).__name__
        code = ('model_access' if name in {'ModelDownloadError', 'GatedRepoError'} else
                'model_download' if name in {'ProxyError', 'ConnectError', 'HfHubHTTPError', 'LocalEntryNotFoundError'} else
                'worker_failed')
        # Do not expose signed URLs, headers, environment values or tracebacks.
        emit(dict(type='error', code=code))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
