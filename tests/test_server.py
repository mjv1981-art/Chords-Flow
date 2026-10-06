import importlib
import time
from pathlib import Path
from unittest.mock import Mock

from fastapi.testclient import TestClient
import pytest

from server.transcription import AudioScore, TranscriptionError, assemble_song, recognize_chunk, youtube_url

backend = importlib.import_module('server.app')
client = TestClient(backend.app)


@pytest.fixture(autouse=True)
def clean_jobs(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('BAYANFLOW_ACCESS_PASSWORD', raising=False)
    monkeypatch.delenv('BAYANFLOW_PUBLIC', raising=False)
    with backend.lock:
        backend.jobs.clear()


def score(**changes):
    data = dict(audible_music=True, reason='', key='Dm', tempo=120, time_signature='4/4',
                notes=[dict(midi=62, start=0, duration=.5), dict(midi=65, start=.5, duration=.5)],
                harmony=[dict(chord='Dm', start=0, duration=2)])
    return AudioScore(**(data | changes))


@pytest.mark.parametrize('url', ['https://youtu.be/abcdefghijk?t=4', 'https://www.youtube.com/watch?v=abcdefghijk&list=whatever',
                               'https://music.youtube.com/watch?v=abcdefghijk', 'https://youtube.com/shorts/abcdefghijk'])
def test_video_urls(url):
    assert youtube_url(url) == 'https://www.youtube.com/watch?v=abcdefghijk'


@pytest.mark.parametrize('url', ['https://youtube.com.evil.test/watch?v=abcdefghijk', 'http://youtube.com/watch?v=abcdefghijk',
                               'https://127.0.0.1/audio', 'file:///etc/passwd', 'https://u:p@youtube.com/watch?v=abcdefghijk',
                               'https://youtube.com:8000/watch?v=abcdefghijk', 'https://youtu.be/not-an-id'])
def test_arbitrary_hosts_and_invalid_ids_rejected(url):
    with pytest.raises(TranscriptionError):
        youtube_url(url)


def test_merge_chunks_uses_seconds_once_and_coalesces_harmony():
    result = assemble_song([(0, 2, score()), (2, 2, score())], {'title': 'Fixture'}, 'https://youtu.be/abcdefghijk')
    assert [n['time'] for n in result['right_hand']] == [0, 1, 4, 5]
    assert result['right_hand'][0]['note'] == 'D4'
    assert result['harmony'] == [dict(chord='Dm', time=0, duration=8)]


def test_no_music_is_not_replaced_with_invented_notes():
    with pytest.raises(TranscriptionError):
        assemble_song([(0, 2, score(audible_music=False, notes=[], harmony=[dict(chord='N', start=0, duration=2)]))], {}, '')


def test_overlap_and_harmony_gaps_rejected():
    with pytest.raises(TranscriptionError):
        assemble_song([(0, 2, score(notes=[dict(midi=60,start=0,duration=1),dict(midi=61,start=.2,duration=1)]))], {}, '')
    with pytest.raises(TranscriptionError):
        assemble_song([(0, 2, score(harmony=[dict(chord='Dm',start=.5,duration=1.5)]))], {}, '')


def test_missing_credentials_and_unknown_job():
    assert client.get('/api/health').json()['transcription_configured'] is False
    response = client.post('/api/transcriptions', json={'url': 'https://youtu.be/abcdefghijk'})
    assert response.status_code == 503
    assert 'GEMINI_API_KEY' in response.json()['detail']
    assert client.get('/api/transcriptions/unknown').status_code == 404


def test_job_completes_with_controlled_audio_service(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-placeholder')
    result = assemble_song([(0,2,score())], {'title':'Fixture'}, 'https://youtu.be/abcdefghijk')
    monkeypatch.setattr(backend, 'transcribe', lambda url, progress: result)
    response = client.post('/api/transcriptions', json={'url':'https://youtu.be/abcdefghijk'})
    assert response.status_code == 202
    for _ in range(50):
        job = client.get('/api/transcriptions/' + response.json()['id']).json()
        if job['status'] != 'processing':
            break
        time.sleep(.01)
    assert job['status'] == 'complete'
    assert job['song'] == result


def test_job_failure_does_not_expose_internal_exception(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-placeholder')
    def fail(url, progress):
        raise RuntimeError('secret-value')
    monkeypatch.setattr(backend, 'transcribe', fail)
    response = client.post('/api/transcriptions', json={'url':'https://youtu.be/abcdefghijk'})
    for _ in range(50):
        job = client.get('/api/transcriptions/' + response.json()['id']).json()
        if job['status'] != 'processing':
            break
        time.sleep(.01)
    assert job['status'] == 'failed'
    assert 'secret-value' not in str(job)


def test_gemini_receives_real_audio_and_validates_response(monkeypatch, tmp_path):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-placeholder')
    clip = tmp_path / 'clip.mp3'
    clip.write_bytes(b'test-audio-bytes')
    response = Mock(status_code=200)
    response.json.return_value = {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':score().model_dump_json()}]}}]}
    post = Mock(return_value=response)
    monkeypatch.setattr('server.transcription.httpx.post', post)
    assert recognize_chunk(clip,2).key == 'Dm'
    parts = post.call_args.kwargs['json']['contents'][0]['parts']
    assert parts[1]['inline_data']['data'] == 'dGVzdC1hdWRpby1ieXRlcw=='
    assert 'title' not in post.call_args.kwargs['json']
    response.json.return_value['candidates'][0]['finishReason'] = 'MAX_TOKENS'
    with pytest.raises(TranscriptionError):
        recognize_chunk(clip,2)


def test_real_ffmpeg_audio_segmentation_and_complete_pipeline(monkeypatch, tmp_path):
    import subprocess
    import server.transcription as pipeline
    audio = tmp_path / 'actual-audio.wav'
    subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i',
                    'sine=frequency=293.665:duration=2',str(audio)], check=True)
    monkeypatch.setenv('GEMINI_API_KEY','test-placeholder')
    monkeypatch.setattr(pipeline,'download_audio',lambda url,folder: (audio,{'title':'Tone fixture','duration':2}))
    seen = []
    def provider(clip, duration, context):
        assert clip.exists() and clip.stat().st_size > 1000
        assert clip.read_bytes().startswith(b'ID3')
        assert duration == 2
        seen.append(clip)
        return score()
    monkeypatch.setattr(pipeline,'recognize_chunk',provider)
    updates = []
    result = pipeline.transcribe('https://youtu.be/abcdefghijk',updates.append)
    assert result['right_hand'][0]['note'] == 'D4'
    assert result['harmony'][0]['chord'] == 'Dm'
    assert len(updates) >= 3
    assert not seen[0].exists()  # Temporary audio is removed on completion.


def test_silent_intro_does_not_set_the_song_key_or_tempo():
    silent = score(audible_music=False, key='C', tempo=80, notes=[], harmony=[dict(chord='N',start=0,duration=2)])
    result = assemble_song([(0,2,silent),(2,2,score())],{},'')
    assert result['key'] == 'Dm'
    assert result['tempo'] == 120
    assert result['harmony'][0]['chord'] == 'N'


def test_public_hosting_without_optional_password_is_supported():
    with TestClient(backend.app) as hosted:
        assert hosted.get('/api/health').status_code == 200
        assert hosted.get('/api/transcriptions/unknown').status_code == 404


def test_hosted_pages_and_jobs_require_password_but_health_is_available(monkeypatch):
    monkeypatch.setenv('BAYANFLOW_ACCESS_PASSWORD','test-access-password')
    with TestClient(backend.app) as hosted:
        assert hosted.get('/api/health').status_code == 200
        assert hosted.get('/').status_code == 401
        assert hosted.post('/api/transcriptions',json={'url':'https://youtu.be/abcdefghijk'}).status_code == 401
        assert hosted.get('/api/transcriptions/unknown').status_code == 401
        assert hosted.get('/api/transcriptions/unknown',auth=('bayanflow','test-access-password')).status_code == 404
        assert hosted.get('/api/transcriptions/unknown',auth=('bayanflow','wrong-password')).status_code == 401


@pytest.mark.parametrize('authorization',['Basic invalid-base64','Bearer random','Basic /w=='])
def test_malformed_authorization_is_rejected(monkeypatch, authorization):
    monkeypatch.setenv('BAYANFLOW_ACCESS_PASSWORD','test-access-password')
    assert client.get('/',headers={'Authorization':authorization}).status_code == 401
