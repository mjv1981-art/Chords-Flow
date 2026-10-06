import json
from pathlib import Path
from unittest.mock import Mock

from fastapi.testclient import TestClient
import httpx
import mido
import pytest

from server.app import app
from server.midi_arrangement import convert_midi
from server.song_library import catalogue, find_songs, library_song

client = TestClient(app)
VIDEO = 'https://www.youtube.com/watch?v=nET3Q1qGie8'


@pytest.fixture(autouse=True)
def no_keys(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('BAYANFLOW_ACCESS_PASSWORD', raising=False)


def test_oembed_title_finds_existing_song_without_audio_ai(monkeypatch):
    response = Mock()
    response.json.return_value = {'title': 'Sleeping Sun - Nightwish (Acapella cover by Julie Elven)', 'author_name': 'Julie Elven'}
    get = Mock(return_value=response)
    monkeypatch.setattr('server.song_library.httpx.get', get)
    ai = Mock(side_effect=AssertionError('Audio AI must never run'))
    monkeypatch.setattr('server.transcription.httpx.post', ai)
    result = client.post('/api/song-lookup', json={'url':VIDEO+'&list=playlist'}).json()
    assert result['video']['metadata_available'] is True
    assert result['matches'][0]['id'] == 'nightwish-sleeping-sun'
    assert 'song' not in result  # Confirmation precedes opening the arrangement.
    assert get.call_args.kwargs['params']['url'] == VIDEO
    assert not ai.called


def test_blocked_title_lookup_can_be_corrected_manually(monkeypatch):
    get = Mock(side_effect=httpx.ConnectError('blocked proxy'))
    monkeypatch.setattr('server.song_library.httpx.get', get)
    result = client.post('/api/song-lookup', json={'url':VIDEO}).json()
    assert result['needs_name'] is True
    assert result['video']['metadata_available'] is False
    assert result['matches'] == []
    result = client.post('/api/song-lookup', json={'url':VIDEO, 'query':'Nightwish — Sleeping Sun'}).json()
    assert result['needs_name'] is False
    assert result['manual_name'] is True
    assert result['matches'][0]['title'] == 'Sleeping Sun'
    assert get.call_count == 1


def test_unknown_song_offers_source_search_without_inventing_music():
    response = client.post('/api/song-lookup', json={'url':VIDEO,'query':'Unknown artist — Unknown tune'})
    assert response.status_code == 200
    result = response.json()
    assert result['matches'] == []
    assert [link['label'] for link in result['search_links']] == ['Аккорды','MIDI','Ноты MusicXML']
    assert 'song' not in result
    assert client.post('/api/library-song', json={'url':VIDEO,'song_id':'unknown-tune'}).status_code == 404


def test_title_matching_respects_word_boundaries_and_cover_me_alias():
    assert find_songs('NIGHTWISH / Sleeping Sun [live]')[0]['id'] == 'nightwish-sleeping-sun'
    assert find_songs('Nightwish - Cover Me')[0]['id'] == 'nightwish-come-cover-me'
    assert not find_songs('Sleeping Sunshine')
    assert not find_songs('NotSleeping Sun')


@pytest.mark.parametrize('entry', catalogue(), ids=lambda entry:entry['id'])
def test_confirmed_library_song_has_source_continuous_chords_and_one_voice(entry):
    response = client.post('/api/library-song', json={'url':VIDEO,'song_id':entry['id']})
    assert response.status_code == 200
    song = response.json()['song']
    assert song['source_url'] == VIDEO
    assert song['arrangement_source_url'] == entry['source_url']
    assert len(song['source_midi_sha256']) == 64
    assert song['right_hand'] and song['harmony']
    end = 0
    for note in song['right_hand']:
        assert note['time'] >= end
        assert note['duration'] >= .5
        end = note['time'] + note['duration']
    cursor = 0
    for chord in song['harmony']:
        assert chord['time'] == cursor
        assert chord['duration'] > 0
        cursor += chord['duration']
    assert cursor >= end


@pytest.mark.parametrize('url',['https://evil.test/watch?v=nET3Q1qGie8','https://youtube.com:9000/watch?v=nET3Q1qGie8'])
def test_metadata_lookup_never_fetches_arbitrary_user_hosts(monkeypatch,url):
    get=Mock()
    monkeypatch.setattr('server.song_library.httpx.get',get)
    assert client.post('/api/song-lookup',json={'url':url}).status_code == 422
    assert not get.called


def test_request_cannot_select_an_arbitrary_score_file():
    assert client.post('/api/library-song',json={'url':VIDEO,'song_id':'../../.env'}).status_code == 422


def test_symbolic_import_preserves_voice_simplifies_polyphony_and_uses_written_harmony(tmp_path):
    source = tmp_path/'fixture.mid'
    midi=mido.MidiFile(ticks_per_beat=480)
    metadata=mido.MidiTrack()
    metadata.extend([mido.MetaMessage('set_tempo',tempo=500000),mido.MetaMessage('time_signature',numerator=4,denominator=4),
                     mido.MetaMessage('key_signature',key='Dm')])
    voice=mido.MidiTrack()
    voice.extend([mido.Message('note_on',note=62,velocity=80,time=0),mido.Message('note_on',note=65,velocity=80,time=0),
                  mido.Message('note_off',note=62,time=480),mido.Message('note_off',note=65,time=0),
                  mido.Message('note_on',note=69,velocity=80,time=0),mido.Message('note_off',note=69,time=480)])
    harmony=mido.MidiTrack()
    harmony.extend([mido.Message('note_on',note=pitch,velocity=70,time=0) for pitch in [38,53,57]])
    harmony.extend([mido.Message('note_off',note=pitch,time=1920 if i==0 else 0) for i,pitch in enumerate([38,53,57])])
    midi.tracks.extend([metadata,voice,harmony])
    midi.save(source)
    song=convert_midi(source,title='Fixture',artist='Fixture',melody_track=1,harmony_tracks=[2])
    assert song['right_hand']==[{'note':'F4','time':0,'duration':1},{'note':'A4','time':1,'duration':1}]
    assert song['harmony']==[{'chord':'Dm','time':0,'duration':2}]
    assert song['key']=='Dm' and song['key_estimated'] is False
    assert song['tempo']==120
    # F-C power harmony in D minor has no third; use the diatonic F major,
    # rather than assigning minor quality to every chord in a minor-key song.
    for message in harmony:
        if message.type in {'note_on','note_off'}:
            message.note = {38:41,53:53,57:60}[message.note]
    midi.save(source)
    simple = convert_midi(source,title='Fixture',artist='Fixture',melody_track=1,harmony_tracks=[2])
    assert simple['harmony'][0]['chord'] == 'F'
