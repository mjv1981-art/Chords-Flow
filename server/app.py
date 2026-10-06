import copy
import base64
import binascii
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import shutil
import secrets
import threading
import time
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from .transcription import TranscriptionError, transcribe, youtube_url

load_dotenv(Path(__file__).resolve().parent.parent / '.env', override=False)


app = FastAPI(title='BayanFlow')


@app.middleware('http')
async def protect_preview(request, call_next):
    password = os.environ.get('BAYANFLOW_ACCESS_PASSWORD')
    # Health checks need no credentials; neither keys nor passwords are returned.
    if not password or request.url.path == '/api/health':
        return await call_next(request)
    try:
        scheme, encoded = request.headers.get('authorization', '').split(' ', 1)
        if scheme.lower() != 'basic':
            raise ValueError()
        user, supplied = base64.b64decode(encoded, validate=True).decode('utf-8').split(':', 1)
        valid = secrets.compare_digest(user.encode(), b'bayanflow') and secrets.compare_digest(supplied.encode(), password.encode())
    except (ValueError, UnicodeDecodeError, binascii.Error):
        valid = False
    if not valid:
        return Response(status_code=401, headers={
            'WWW-Authenticate': 'Basic realm="BayanFlow", charset="UTF-8"',
            'Cache-Control': 'no-store',
        })
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    return response

jobs: dict = {}
lock = threading.RLock()
executor = ThreadPoolExecutor(max_workers=2)


class Request(BaseModel):
    url: str = Field(max_length=2048)


@app.get('/api/health')
def health():
    return {'status': 'ok', 'transcription_configured': bool(os.environ.get('GEMINI_API_KEY')),
            'transcription_source': 'gemini_youtube',
            'ffmpeg_available': bool(shutil.which('ffmpeg') and shutil.which('ffprobe'))}


def process(job_id: str, url: str):
    def progress(message):
        with lock:
            if isinstance(message, dict):
                jobs[job_id].update(message)
            else:
                jobs[job_id]['progress'] = message
    try:
        song = transcribe(url, progress)
        with lock:
            if song.get('transcription_partial'):
                jobs[job_id].update(status='partial', song=song, error=song['transcription_warning'])
            else:
                jobs[job_id].update(status='complete', song=song)
    except TranscriptionError as error:
        with lock:
            jobs[job_id].update(status='failed', error=str(error))
    except Exception:
        # Do not leak provider response bodies, credentials, or internal paths.
        with lock:
            jobs[job_id].update(status='failed', error='Не удалось обработать аудио. Попробуйте другую ссылку.')


@app.post('/api/transcriptions', status_code=202)
def create(request: Request):
    try:
        url = youtube_url(request.url)
    except TranscriptionError as error:
        raise HTTPException(422, str(error)) from None
    if not os.environ.get('GEMINI_API_KEY'):
        raise HTTPException(503, 'Распознавание не настроено. Добавьте GEMINI_API_KEY в настройках сервера.')
    with lock:
        now = time.time()
        for job_id in list(jobs):
            if jobs[job_id]['status'] != 'processing' and now - jobs[job_id]['created'] > 3600:
                del jobs[job_id]
        if sum(j['status'] == 'processing' for j in jobs.values()) >= 2:
            raise HTTPException(429, 'Сервис занят. Дождитесь завершения текущего распознавания.')
        if len(jobs) >= 100:
            oldest = next((i for i, j in jobs.items() if j['status'] != 'processing'), None)
            if oldest:
                del jobs[oldest]
        job_id = uuid.uuid4().hex
        jobs[job_id] = {'id': job_id, 'status': 'processing', 'created': now, 'progress': 'Открываем видео через Gemini…'}
        executor.submit(process, job_id, url)
    return {'id': job_id}


@app.get('/api/transcriptions/{job_id}')
def read(job_id: str):
    with lock:
        if job_id not in jobs:
            raise HTTPException(404, 'Задание не найдено. Отправьте ссылку заново.')
        result = copy.deepcopy(jobs[job_id])
        result.pop('created', None)
        return result


# Built application can be served by one process. Dev mode uses Vite's /api proxy.
dist = Path(__file__).resolve().parent.parent / 'dist'
if dist.is_dir():
    app.mount('/', StaticFiles(directory=dist, html=True), name='frontend')
