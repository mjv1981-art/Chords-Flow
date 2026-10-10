import base64
import binascii
import os
from pathlib import Path
import secrets
import asyncio
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from .transcription import TranscriptionError
from .song_library import catalogue, library_song, lookup
from . import muscriptor_jobs as jobs
from .practice_arrangement import MAX_MIDI_BYTES, arrange_midi, midi_material

load_dotenv(Path(__file__).resolve().parent.parent / '.env', override=False)


@asynccontextmanager
async def lifespan(app):
    yield
    await asyncio.to_thread(jobs.shutdown)


app = FastAPI(title='BayanFlow', lifespan=lifespan)


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


Instrument = Literal['voice', 'acoustic_piano', 'flutes', 'violin', 'acoustic_guitar']


class TranscriptionRequest(Request):
    start: float = Field(default=0, ge=0, le=570, allow_inf_nan=False)
    seconds: Literal[30, 60] = 30
    instrument: Instrument = 'voice'
    title: str = Field(default='', max_length=200)


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
    return {'status': 'ok', 'mode': 'muscriptor', 'library_count': len(catalogue()), 'ai_required': False,
            'transcription': jobs.readiness(), 'midi_import_available': True}


@app.post('/api/transcriptions')
def start_transcription(request: TranscriptionRequest):
    job_id, _, options = reserve_job(**request.model_dump())
    jobs.launch(job_id, options)
    return jobs.status(job_id)


def reserve_job(**options):
    try:
        return jobs.reserve(**options)
    except BlockingIOError as error:
        raise HTTPException(429, str(error)) from None
    except jobs.SetupRequired as error:
        raise HTTPException(503, str(error)) from None
    except TranscriptionError as error:
        raise HTTPException(422, str(error)) from None


@app.post('/api/transcriptions/upload')
async def upload_transcription(file: UploadFile = File(...), start: float = Form(0, ge=0, le=570),
                               seconds: Literal[30, 60] = Form(30), instrument: Instrument = Form('voice')):
    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.aac', '.mp4', '.webm'}:
        await file.close()
        raise HTTPException(422, 'Выберите аудио: MP3, WAV, M4A, FLAC, OGG, AAC, MP4 или WebM.')
    job_id, folder, options = reserve_job(start=start, seconds=seconds, instrument=instrument,
                                          title=Path(file.filename or 'Запись').stem)
    path, size = folder / ('upload' + suffix), 0
    try:
        with path.open('wb') as output:
            path.chmod(0o600)
            while block := await file.read(1024 * 1024):
                size += len(block)
                if size > jobs.MAX_AUDIO_BYTES:
                    raise HTTPException(413, 'Аудиофайл должен быть меньше 50 МБ.')
                output.write(block)
        if not size:
            raise HTTPException(422, 'Аудиофайл пустой.')
    except BaseException:
        jobs.abandon(job_id)
        raise
    finally:
        await file.close()
    jobs.launch(job_id, options, path)
    return jobs.status(job_id)


@app.get('/api/transcriptions/{job_id}')
def transcription_status(job_id: str):
    try:
        return jobs.status(job_id)
    except KeyError:
        raise HTTPException(404, 'Распознавание не найдено. Отправьте запись ещё раз.') from None


@app.delete('/api/transcriptions/{job_id}')
def cancel_transcription(job_id: str):
    try:
        return jobs.cancel(job_id)
    except KeyError:
        raise HTTPException(404, 'Распознавание не найдено.') from None


async def midi_bytes(file):
    try:
        data = await file.read(MAX_MIDI_BYTES + 1)
        if len(data) > MAX_MIDI_BYTES:
            raise HTTPException(413, 'MIDI-файл должен быть меньше 2 МБ.')
        return data
    finally:
        await file.close()


@app.post('/api/midi/inspect')
async def inspect_midi(file: UploadFile = File(...)):
    try:
        material = midi_material(await midi_bytes(file))
        return {key: material[key] for key in ['tracks', 'tempo', 'meter', 'key', 'tempo_changes']}
    except TranscriptionError as error:
        raise HTTPException(422, str(error)) from None


@app.post('/api/midi/arrange')
async def import_midi(file: UploadFile = File(...), track: int = Form(..., ge=0, le=127)):
    try:
        title = Path(file.filename or 'MuScriptor').stem[:200]
        song = arrange_midi(await midi_bytes(file), track, title)
        return {'song': song}
    except TranscriptionError as error:
        raise HTTPException(422, str(error)) from None


# Built application can be served by one process. Dev mode uses Vite's /api proxy.
dist = Path(__file__).resolve().parent.parent / 'dist'
if dist.is_dir():
    app.mount('/', StaticFiles(directory=dist, html=True), name='frontend')
