import base64
import binascii
import os
from pathlib import Path
import secrets

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from .transcription import TranscriptionError
from .song_library import catalogue, library_song, lookup

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

class Request(BaseModel):
    url: str = Field(max_length=2048)


class SongLookup(Request):
    query: str = Field(default='', max_length=200)


class LibrarySelection(Request):
    song_id: str = Field(min_length=1, max_length=80, pattern=r'^[a-z0-9-]+$')


@app.post('/api/song-lookup')
def identify_song(request: SongLookup):
    try:
        return lookup(request.url, request.query)
    except TranscriptionError as error:
        raise HTTPException(422, str(error)) from None


@app.post('/api/library-song')
def open_library_song(request: LibrarySelection):
    try:
        return {'song': library_song(request.song_id, request.url)}
    except TranscriptionError as error:
        raise HTTPException(404, str(error)) from None


@app.get('/api/health')
def health():
    return {'status': 'ok', 'mode': 'song_library', 'library_count': len(catalogue()), 'ai_required': False}


@app.post('/api/transcriptions')
def retired_transcription(request: Request):
    raise HTTPException(410, 'Распознавание аудио отключено. Обновите страницу и выберите готовую аранжировку песни.')


@app.get('/api/transcriptions/{job_id}')
def retired_job(job_id: str):
    raise HTTPException(410, 'Распознавание аудио отключено. Обновите страницу.')


# Built application can be served by one process. Dev mode uses Vite's /api proxy.
dist = Path(__file__).resolve().parent.parent / 'dist'
if dist.is_dir():
    app.mount('/', StaticFiles(directory=dist, html=True), name='frontend')
