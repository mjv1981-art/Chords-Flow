import base64
import io
import json
from pathlib import Path
import sys
import threading
import time
import wave

from fastapi.testclient import TestClient
import mido
import pytest

from server.app import app
from server import muscriptor_jobs as jobs
from server.practice_arrangement import arrange_midi, midi_material, simple_arrangement
from server.transcription import TranscriptionError

client = TestClient(app)
VIDEO = 'https://youtu.be/abcdefghijk'
EXPORT = base64.b64decode(json.loads((Path(__file__).parent / 'fixtures/muscriptor-export.json').read_text())['midi_base64'])


@pytest.fixture(autouse=True)
def isolate(monkeypatch, tmp_path):
    monkeypatch.setenv('BAYANFLOW_CACHE_DIR', str(tmp_path))
    monkeypatch.delenv('BAYANFLOW_ACCESS_PASSWORD', raising=False)
    yield
    jobs.shutdown()


def ready(monkeypatch):
    monkeypatch.setattr(jobs, 'readiness', lambda:dict(configured=True, model='small', reason=''))


def test_real_muscriptor_midi_export_can_be_inspected_and_arranged_without_model_access(monkeypatch):
    monkeypatch.setattr(jobs, 'readiness', lambda:dict(configured=False, model='small', reason='model_access'))
    response = client.post('/api/midi/inspect', files={'file':('export.mid',EXPORT,'audio/midi')})
    assert response.status_code == 200
    tracks = response.json()['tracks']
    voice = next(track for track in tracks if track['voice'])
    assert voice['name'] == 'voice' and voice['notes'] == 3
    response = client.post('/api/midi/arrange', files={'file':('export.mid',EXPORT,'audio/midi')}, data={'track':voice['index']})
    assert response.status_code == 200
    song = response.json()['song']
    assert [note['note'] for note in song['right_hand']] == ['D4','F4','A4']
    assert [note['time'] for note in song['right_hand']] == [0,2,4]
    assert song['harmony'][0]['chord'] == 'Dm'
    assert song['harmony_arranged'] is False


def test_midi_tempo_changes_are_integrated_into_note_times():
    midi = mido.MidiFile(ticks_per_beat=480)
    tempo = mido.MidiTrack([mido.MetaMessage('set_tempo',tempo=500000),
                            mido.MetaMessage('set_tempo',tempo=1000000,time=480)])
    voice = mido.MidiTrack([mido.Message('note_on',note=62,velocity=80),
                            mido.Message('note_off',note=62,time=960)])
    midi.tracks.extend([tempo,voice]); buffer=io.BytesIO(); midi.save(file=buffer)
    material = midi_material(buffer.getvalue())
    assert material['notes'][0]['end'] == 1.5
    assert material['tempo'] == 120
    song = arrange_midi(buffer.getvalue(),1,'Tempo fixture')
    assert song['right_hand'][0]['duration'] == 3
    assert song['tempo_estimated'] is True


def test_acappella_harmony_is_labelled_as_an_arrangement_and_rests_remain():
    notes=[dict(midi=62,start=0,end=.5,instrument='voice'),dict(midi=65,start=1,end=1.5,instrument='voice')]
    song=simple_arrangement(notes,melody=lambda note:True,title='Vocal fixture',tempo=120,key='Dm')
    assert song['harmony_arranged'] is True
    assert song['right_hand'][0]['duration'] == 1
    assert song['right_hand'][1]['time'] == 2
    assert 'подобран по мелодии' in song['lyrics_notice']
    assert song['harmony'][-1]['time'] + song['harmony'][-1]['duration'] >= 3


@pytest.mark.parametrize('changes',[{'midi':62.5},{'start':float('nan')},{'end':-1}])
def test_bad_model_notes_do_not_become_a_playable_score(changes):
    with pytest.raises(TranscriptionError):
        simple_arrangement([dict(midi=62,start=0,end=1)|changes],melody=lambda note:True,title='Bad')


def test_melody_instrument_must_exist_in_the_transcription():
    with pytest.raises(TranscriptionError,match='Мелодия не найдена'):
        simple_arrangement([dict(midi=60,start=0,end=1,instrument='acoustic_piano')],
                           melody=lambda note:note['instrument']=='voice',title='Intro')


def test_invalid_and_oversized_midi_are_rejected():
    assert client.post('/api/midi/inspect',files={'file':('bad.mid',b'not midi')}).status_code==422
    assert client.post('/api/midi/inspect',files={'file':('large.mid',b'MThd'+b'x'*(2*1024*1024))}).status_code==413
    assert client.post('/api/midi/arrange',files={'file':('export.mid',EXPORT)},data={'track':127}).status_code==422


def test_jobs_validate_urls_and_have_a_single_inference_slot(monkeypatch):
    ready(monkeypatch)
    monkeypatch.setattr(jobs,'launch',lambda *args:None)
    assert client.post('/api/transcriptions',json={'url':'https://evil.test/audio'}).status_code==422
    response=client.post('/api/transcriptions',json={'url':VIDEO,'start':10,'seconds':30})
    assert response.status_code==200
    job_id=response.json()['id']
    assert client.post('/api/transcriptions',json={'url':VIDEO}).status_code==429
    assert client.delete('/api/transcriptions/'+job_id).json()['status']=='cancelled'
    jobs.abandon(job_id)
    assert client.get('/api/transcriptions/../../.env').status_code in {404,405}


def test_status_survives_a_restart_and_flags_unfinished_work(monkeypatch):
    ready(monkeypatch)
    job_id,_,_=jobs.reserve(url=VIDEO)
    jobs._update(job_id,status='ready',song={'title':'Cached'})
    jobs._active.pop(job_id)
    assert jobs.status(job_id)['song']['title']=='Cached'
    job_id,_,_=jobs.reserve(url=VIDEO)
    jobs._active.pop(job_id)
    assert jobs.status(job_id)['status']=='error'
    assert 'перезапущен' in jobs.status(job_id)['message']


def test_cancellation_stops_the_child_process(tmp_path):
    cancelled=threading.Event()
    timer=threading.Timer(.15,cancelled.set); timer.start()
    began=time.monotonic()
    with pytest.raises(InterruptedError):
        jobs._command([sys.executable,'-c','import time; time.sleep(10)'],tmp_path,cancelled,time.monotonic()+5)
    assert time.monotonic()-began < 2
    timer.join()


def test_audio_job_uses_real_ffmpeg_and_validates_worker_events(monkeypatch,tmp_path):
    ready(monkeypatch)
    job_id,folder,request=jobs.reserve(title='Audio fixture')
    source=folder/'upload.wav'
    with wave.open(str(source),'wb') as audio:
        audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000); audio.writeframes(b'\0\0'*32000)
    original=jobs._command
    calls=[]
    def command(args,folder,cancelled,deadline,**kwargs):
        if args[0]=='ffmpeg': return original(args,folder,cancelled,deadline,**kwargs)
        config=json.loads(Path(args[-1]).read_text()); calls.append(config)
        kwargs['progress'](dict(type='progress',stage='recognizing',message='Fixture',completed=1,total=1))
        Path(config['result']).write_text(json.dumps(dict(notes=[dict(midi=62,start=0,end=1,instrument='voice')],
                                                          tempo=120,tempo_estimated=True,meter='4/4')))
        return b''
    monkeypatch.setattr(jobs,'_command',command)
    jobs._run(job_id,request,source)
    result=jobs.status(job_id)
    assert result['status']=='ready'
    assert result['song']['right_hand'][0]['note']=='D4'
    assert result['song']['excerpt_seconds']==2
    assert not source.exists()
    assert calls[0]['model']=='small'


def test_failed_upload_releases_the_inference_slot(monkeypatch):
    ready(monkeypatch)
    response=client.post('/api/transcriptions/upload',files={'file':('empty.wav',b'')})
    assert response.status_code==422
    assert not jobs._active
