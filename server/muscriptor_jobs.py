"""Bounded, cancellable transcription jobs with persistent status and results."""
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid

from .practice_arrangement import simple_arrangement
from .transcription import TranscriptionError, youtube_url

PROJECT = Path(__file__).resolve().parent.parent
MAX_AUDIO_BYTES = 50 * 1024 * 1024
MAX_JOB_SECONDS = 600
INSTRUMENTS = {'voice', 'acoustic_piano', 'flutes', 'violin', 'acoustic_guitar'}
TERMINAL = {'ready', 'error', 'cancelled'}
_guard = threading.Lock()
_active = {}


class SetupRequired(TranscriptionError):
    pass


def root():
    path = Path(os.environ.get('BAYANFLOW_CACHE_DIR', str(PROJECT / '.cache/transcriptions'))) / 'muscriptor'
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


def worker_python():
    return Path(os.environ.get('MUSCRIPTOR_PYTHON', str(PROJECT / '.venv-muscriptor/bin/python')))


def readiness():
    model = os.environ.get('MUSCRIPTOR_MODEL', 'small')
    if model not in {'small', 'medium', 'large'}:
        return dict(configured=False, reason='invalid_model', model='small')
    runtime = worker_python().is_file()
    cache = Path(os.environ.get('HF_HOME', str(PROJECT / '.cache/huggingface'))) / 'hub'
    cached = any((cache / f'models--MuScriptor--muscriptor-{model}' / 'snapshots').glob('*/model.safetensors'))
    access = bool(os.environ.get('HF_TOKEN') or os.environ.get('HUGGING_FACE_HUB_TOKEN') or cached)
    return dict(configured=runtime and access and bool(shutil.which('ffmpeg')),
                reason='runtime' if not runtime else 'model_access' if not access else 'ffmpeg' if not shutil.which('ffmpeg') else '',
                model=model)


def _folder(job_id):
    if not re.fullmatch(r'[a-f0-9]{32}', job_id):
        raise KeyError(job_id)
    path = root() / job_id
    if not (path / 'status.json').is_file():
        raise KeyError(job_id)
    return path


def _write(folder, data):
    temporary = folder / 'status.tmp'
    temporary.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False))
    temporary.chmod(0o600)
    temporary.replace(folder / 'status.json')


def status(job_id):
    with _guard:
        folder = _folder(job_id)
        data = json.loads((folder / 'status.json').read_text())
        if data['status'] not in TERMINAL and job_id not in _active:
            data.update(status='error', message='Сервер перезапущен. Отправьте запись ещё раз.', updated=time.time())
            _write(folder, data)
        return data


def _update(job_id, **changes):
    with _guard:
        folder = _folder(job_id)
        data = json.loads((folder / 'status.json').read_text())
        if data['status'] in TERMINAL:
            return
        data.update(changes, updated=time.time())
        _write(folder, data)


def cancel(job_id):
    with _guard:
        folder = _folder(job_id)
        data = json.loads((folder / 'status.json').read_text())
        if data['status'] not in TERMINAL:
            if job_id in _active: _active[job_id].set()
            data.update(status='cancelled', message='Распознавание отменено.', updated=time.time())
            _write(folder, data)
        return data


def reserve(*, url='', start=0, seconds=30, instrument='voice', title=''):
    if url: url = youtube_url(url)
    if instrument not in INSTRUMENTS or seconds not in {30, 60} or not 0 <= start <= 570:
        raise TranscriptionError('Выберите фрагмент 30 или 60 секунд и корректное время начала.')
    ready = readiness()
    if not ready['configured']:
        raise SetupRequired('MuScriptor ещё не настроен на сервере. Можно открыть MIDI, экспортированный из MuScriptor.')
    with _guard:
        if _active:
            raise BlockingIOError('Сервер уже распознаёт запись. Дождитесь окончания или отмените её.')
        # Remove only our own old job folders, never unrelated cache files.
        for path in root().iterdir():
            if path.is_dir() and re.fullmatch(r'[a-f0-9]{32}', path.name) and time.time() - path.stat().st_mtime > 86400:
                shutil.rmtree(path)
        job_id = uuid.uuid4().hex
        folder = root() / job_id
        folder.mkdir(mode=0o700)
        now = time.time()
        data = dict(id=job_id, status='preparing', message='Готовим фрагмент записи…', completed=0,
                    total=0, created=now, updated=now)
        _active[job_id] = threading.Event()
        _write(folder, data)
    request = dict(url=url, start=start, seconds=seconds, instrument=instrument, title=title[:200], model=ready['model'])
    return job_id, folder, request


def abandon(job_id):
    cancel(job_id)
    with _guard:
        _active.pop(job_id, None)
    shutil.rmtree(root() / job_id, ignore_errors=True)


def shutdown():
    with _guard:
        for event in _active.values(): event.set()
    end = time.monotonic() + 5
    while time.monotonic() < end:
        with _guard:
            if not _active: return
        time.sleep(.05)


def launch(job_id, request, source=None):
    thread = threading.Thread(target=_run, args=(job_id, request, source), daemon=True)
    thread.start()


def _stop(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=3)


def _command(command, folder, cancelled, deadline, *, progress=None, env=None):
    with open(folder / 'process.log', 'ab', buffering=0) as log:
        os.chmod(folder / 'process.log', 0o600)
        process = subprocess.Popen(command, cwd=PROJECT, stdout=subprocess.PIPE, stderr=log,
                                   start_new_session=True, env=env)
        output, size, pending = [], 0, b''
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        try:
            while selector.get_map():
                if cancelled.is_set(): raise InterruptedError()
                if time.monotonic() > deadline: raise TimeoutError()
                for key, _ in selector.select(.2):
                    block = os.read(key.fileobj.fileno(), 65536)
                    if not block:
                        selector.unregister(key.fileobj)
                        continue
                    size += len(block)
                    if size > 4 * 1024 * 1024:
                        raise TranscriptionError('Ответ обработчика слишком большой.')
                    if progress:
                        pending += block
                        while b'\n' in pending:
                            line, pending = pending.split(b'\n', 1)
                            if line: progress(json.loads(line))
                    else:
                        output.append(block)
            process.wait(timeout=max(.1, min(3, deadline - time.monotonic())))
            if process.returncode:
                raise TranscriptionError('Не удалось обработать запись. Попробуйте аудиофайл или MIDI из MuScriptor.')
            return b''.join(output)
        finally:
            _stop(process)
            selector.close()
            process.stdout.close()


def _youtube_failure(details, stage):
    """Classify private downloader output without exposing URLs, cookies or tokens."""
    text = details.lower()
    prefix = f'YouTube: {stage}. '
    if 'not a bot' in text or 'confirm you’re not a bot' in text:
        return prefix + 'YouTube требует проверку входа для сервера (youtube_bot_check). Распознавание ещё не началось.'
    if any(value in text for value in ('private video', 'video unavailable', 'not available in your country', 'age-restricted', 'sign in to confirm your age', 'members-only')):
        return prefix + 'Видео требует доступа или недоступно в регионе сервера (youtube_video_access).'
    if any(value in text for value in ('javascript runtime', 'n challenge', 'signature solving', 'signature extraction')):
        return prefix + 'Не удалось обработать проверку проигрывателя YouTube (youtube_player_challenge). Нужна проверка Node.js и yt-dlp на сервере.'
    if 'po token' in text or 'po_token' in text:
        return prefix + 'YouTube требует токен доступа к потоку для сервера (youtube_stream_token).'
    if '403' in text or 'forbidden' in text:
        return prefix + 'Сервер получил HTTP 403 (youtube_http_403). Причину нужно проверить на сервере; она может быть связана с сетевым прокси или доступом к потоку.'
    if '429' in text or 'too many requests' in text:
        return prefix + 'YouTube ограничил запросы сервера (youtube_rate_limit).'
    if any(value in text for value in ('timed out', 'timeout', 'unable to resolve', 'name resolution', 'connection refused', 'network is unreachable')):
        return prefix + 'Ошибка сети при получении записи (youtube_network).'
    if 'requested format is not available' in text:
        return prefix + 'Не найден доступный аудиопоток (youtube_audio_format).'
    return prefix + 'Загрузчик не смог получить запись (youtube_download_failed). Распознавание ещё не началось.'


def _youtube_command(command, folder, cancelled, deadline, stage):
    log = folder / 'process.log'
    offset = log.stat().st_size if log.exists() else 0
    try:
        return _command(command, folder, cancelled, deadline)
    except TimeoutError:
        raise TranscriptionError(f'YouTube: {stage}. Превышено время ожидания загрузки (youtube_timeout). Распознавание ещё не началось.') from None
    except TranscriptionError:
        details = ''
        if log.exists():
            with log.open('rb') as stream:
                stream.seek(max(offset, log.stat().st_size - 65536))
                details = stream.read(65536).decode('utf-8', errors='replace')
        raise TranscriptionError(_youtube_failure(details, stage)) from None


def _youtube(request, folder, cancelled, deadline):
    flags = ['--ignore-config', '--no-playlist', '--js-runtimes', 'node', '--socket-timeout', '10', '--retries', '1', '--extractor-retries', '1']
    cookies = os.environ.get('YOUTUBE_COOKIES_FILE')
    if cookies: flags += ['--cookies', cookies]
    base = [sys.executable, '-m', 'yt_dlp', *flags]
    try:
        raw = _youtube_command([*base, '--dump-single-json', '--skip-download', request['url']], folder, cancelled,
                       min(deadline, time.monotonic() + 45), 'получение информации о видео')
        metadata = json.loads(raw)
        if not isinstance(metadata, dict):
            raise ValueError()
        duration = float(metadata.get('duration') or 0)
    except (ValueError, TypeError):
        raise TranscriptionError('YouTube вернул некорректные сведения о видео (youtube_metadata).') from None
    if metadata.get('is_live') or not 0 < duration <= 600 or request['start'] >= duration:
        raise TranscriptionError('Выберите обычное видео до 10 минут и фрагмент внутри записи.')
    request['title'] = str(metadata.get('title') or 'YouTube')[:200]
    _youtube_command([*base, '--quiet', '--no-warnings', '-f', 'bestaudio/best', '--max-filesize', '100M',
                  '--download-sections', f"*{request['start']}-{request['start'] + request['seconds']}",
                  '-o', str(folder / 'youtube.%(ext)s'), request['url']], folder, cancelled,
                 min(deadline, time.monotonic() + 120), 'загрузка аудиофрагмента')
    source = next((path for path in folder.glob('youtube.*') if path.suffix not in {'.part', '.ytdl'} and path.stat().st_size), None)
    if source is None:
        raise TranscriptionError('Загрузчик завершился без аудиофайла (youtube_empty_audio).')
    return source


def _run(job_id, request, source):
    folder = root() / job_id
    with _guard:
        cancelled = _active[job_id]
    deadline = time.monotonic() + MAX_JOB_SECONDS
    try:
        youtube = source is None
        if youtube: source = _youtube(request, folder, cancelled, deadline)
        audio = folder / 'excerpt.wav'
        _command(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y',
                  '-ss', '0' if youtube else str(request['start']), '-i', str(source),
                  '-t', str(request['seconds']), '-vn', '-ac', '1', '-ar', '16000', str(audio)],
                 folder, cancelled, min(deadline, time.monotonic() + 45))
        if not audio.is_file() or audio.stat().st_size < 3200:
            raise TranscriptionError('Фрагмент пустой. Проверьте время начала записи.')
        import wave
        with wave.open(str(audio)) as recording:
            excerpt_seconds = recording.getnframes() / recording.getframerate()
        identity = hashlib.sha256(audio.read_bytes() + json.dumps([request['model'], request['instrument'], 'muscriptor-0.3.0-practice-v1']).encode()).hexdigest()
        results = root() / 'results'
        results.mkdir(exist_ok=True, mode=0o700)
        cached = results / f'{identity}.json'
        if cached.exists() and time.time() - cached.stat().st_mtime < 7 * 86400:
            song = json.loads(cached.read_text())
        else:
            result = folder / 'notes.json'
            config = dict(audio=str(audio), result=str(result), midi=str(folder / 'transcription.mid'), model=request['model'])
            (folder / 'worker.json').write_text(json.dumps(config))
            env = dict(os.environ)
            env.setdefault('HF_HOME', str(PROJECT / '.cache/huggingface'))
            env.setdefault('HF_HUB_DISABLE_XET', '1')
            env.setdefault('TORCH_HOME', str(PROJECT / '.cache/torch'))
            if not env.get('HF_TOKEN') and not env.get('HUGGING_FACE_HUB_TOKEN'):
                env.setdefault('HF_HUB_OFFLINE', '1')
            def progress(event):
                if event['type'] == 'error':
                    messages = {
                        'model_access': 'Нет доступа к модели. Примите лицензию MuScriptor и настройте HF_TOKEN на сервере.',
                        'model_download': 'Сервер не смог скачать модель. Проверьте доступ к Hugging Face; можно открыть MIDI из MuScriptor.',
                    }
                    message = messages.get(event.get('code'), 'MuScriptor не смог распознать запись. Можно открыть экспортированный MIDI.')
                    raise TranscriptionError(message)
                if event['type'] == 'progress':
                    _update(job_id, status=event['stage'], message=event['message'],
                            completed=event.get('completed', 0), total=event.get('total', 0))
            _command([str(worker_python()), '-m', 'server.muscriptor_worker', str(folder / 'worker.json')],
                     folder, cancelled, deadline, progress=progress, env=env)
            material = json.loads(result.read_text())
            song = simple_arrangement(material['notes'], melody=lambda note:note.get('instrument') == request['instrument'],
                                      title=request['title'] or 'Запись', tempo=material['tempo'],
                                      meter=material['meter'], tempo_estimated=material['tempo_estimated'])
            song['meter_estimated'] = material.get('meter_estimated', True)
            if song['meter_estimated']:
                song['lyrics_notice'] += ' Размер выбран для учебной версии.'
            temporary = cached.with_suffix('.tmp')
            temporary.write_text(json.dumps(song, ensure_ascii=False, allow_nan=False))
            temporary.chmod(0o600); temporary.replace(cached)
        song.update(title=request['title'] or 'Запись', source_url=request['url'],
                    excerpt_start=request['start'], excerpt_seconds=round(excerpt_seconds, 2))
        _update(job_id, status='ready', message='Мелодия готова.', song=song)
    except InterruptedError:
        _update(job_id, status='cancelled', message='Распознавание отменено.')
    except TimeoutError:
        _update(job_id, status='error', message='Обработка заняла слишком долго. Попробуйте 30 секунд или MIDI из MuScriptor.')
    except TranscriptionError as error:
        _update(job_id, status='error', message=str(error))
    except Exception:
        _update(job_id, status='error', message='Не удалось обработать запись. Попробуйте другой фрагмент или MIDI из MuScriptor.')
    finally:
        for path in folder.iterdir():
            if path.name != 'status.json': path.unlink(missing_ok=True)
        with _guard:
            _active.pop(job_id, None)
