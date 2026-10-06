import importlib
import time
from pathlib import Path
from unittest.mock import Mock

from fastapi.testclient import TestClient
import pytest

from server.transcription import AudioScore, TranscriptionError, VideoMetadata, assemble_song, recognize_chunk, video_metadata, youtube_url

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
    monkeypatch.setattr(backend.shutil, 'which', lambda tool: None)
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


def test_native_youtube_pipeline_segments_video_and_carries_musical_context(monkeypatch):
    import server.transcription as pipeline
    monkeypatch.setattr(pipeline, 'video_metadata', lambda url: VideoMetadata(
        accessible=True, reason='', title='Video fixture', uploader='', duration=62, is_live=False))
    seen = []
    def provider(url, duration, context, *, offset):
        assert url == 'https://www.youtube.com/watch?v=abcdefghijk'
        seen.append((offset, duration, context))
        return score(harmony=[dict(chord='Dm', start=0, duration=duration)])
    monkeypatch.setattr(pipeline,'recognize_chunk',provider)
    updates = []
    result = pipeline.transcribe('https://youtu.be/abcdefghijk',updates.append)
    assert result['right_hand'][0]['note'] == 'D4'
    assert result['harmony'][0]['chord'] == 'Dm'
    assert result['title'] == 'Video fixture'
    assert [item[:2] for item in seen] == [(0,30),(30,30),(60,2)]
    assert seen[0][2] is None
    assert seen[1][2] == seen[2][2] == dict(key='Dm', tempo=120, time_signature='4/4')
    assert len(updates) == 5


def test_gemini_native_youtube_input_has_clip_offsets_and_relative_timing(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-placeholder')
    response = Mock(status_code=200)
    response.json.return_value = {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':score().model_dump_json()}]}}]}
    post = Mock(return_value=response)
    monkeypatch.setattr('server.transcription.httpx.post', post)
    assert recognize_chunk('https://youtu.be/abcdefghijk?list=ignored', 2, offset=30).key == 'Dm'
    parts = post.call_args.kwargs['json']['contents'][0]['parts']
    assert parts[1] == {'fileData': {'fileUri': 'https://www.youtube.com/watch?v=abcdefghijk'},
                        'videoMetadata': {'startOffset': '30.000s', 'endOffset': '32.000s'}}
    assert 'relative to THIS segment' in parts[0]['text']


@pytest.mark.parametrize('changes', [{'accessible': False}, {'duration': 0}, {'duration': 601},
                                   {'duration': float('nan')}, {'is_live': True}])
def test_native_video_metadata_rejects_unavailable_live_or_invalid_duration(monkeypatch, changes):
    import json
    monkeypatch.setenv('GEMINI_API_KEY', 'test-placeholder')
    data = dict(accessible=True, reason='', title='Fixture', uploader='', duration=62, is_live=False) | changes
    response = Mock(status_code=200)
    response.json.return_value = {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(data)}]}}]}
    monkeypatch.setattr('server.transcription.httpx.post', Mock(return_value=response))
    with pytest.raises(TranscriptionError):
        video_metadata('https://youtu.be/abcdefghijk')


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
