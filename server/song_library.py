"""Identify songs from video titles and load existing symbolic arrangements."""
import copy
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlencode

import httpx

from .transcription import TranscriptionError, youtube_url

LIBRARY = Path(__file__).parent / 'library'


def catalogue():
    return json.loads((LIBRARY / 'manifest.json').read_text())


def normalized(text):
    return ' '.join(re.findall(r'\w+', unicodedata.normalize('NFKC', text).casefold()))


def find_songs(query):
    query = normalized(query)
    results = []
    for entry in catalogue():
        aliases = [entry['title'], *entry.get('aliases', [])]
        if not query or any(f' {normalized(alias)} ' in f' {query} ' for alias in aliases):
            results.append({key: entry[key] for key in ['id', 'title', 'artist', 'description', 'source_url', 'source_name']})
    return results


def lookup(raw_url, query=''):
    url = youtube_url(raw_url)
    title, author = '', ''
    metadata_available = False
    if not query.strip():
        try:
            response = httpx.get('https://www.youtube.com/oembed', params={'url': url, 'format': 'json'},
                                 timeout=httpx.Timeout(10, connect=5), follow_redirects=False)
            response.raise_for_status()
            data = response.json()
            if isinstance(data.get('title'), str) and data['title'].strip():
                title = data['title'].strip()[:500]
                author = str(data.get('author_name', ''))[:200]
                metadata_available = True
        except (httpx.HTTPError, ValueError, TypeError):
            pass
    search = query.strip()[:200] or title
    links = []
    if search:
        for label, suffix in [('Аккорды', 'chords'), ('MIDI', 'MIDI download'), ('Ноты MusicXML', 'sheet music MusicXML')]:
            links.append({'label': label, 'url': 'https://www.google.com/search?' + urlencode({'q': search + ' ' + suffix})})
    return {'video': {'url': url, 'title': title, 'author': author, 'metadata_available': metadata_available},
            'query': search, 'matches': find_songs(search) if search else [], 'search_links': links,
            'library_count': len(catalogue()),
            'needs_name': not bool(search), 'manual_name': bool(query.strip())}


def library_song(song_id, raw_url):
    url = youtube_url(raw_url)
    entry = next((song for song in catalogue() if song['id'] == song_id), None)
    if entry is None:
        raise TranscriptionError('Для этой песни пока нет проверенной аранжировки в библиотеке.')
    # Filenames belong to the maintained manifest, never to request input.
    song = json.loads((LIBRARY / entry['arrangement_file']).read_text())
    result = copy.deepcopy(song)
    result.update(source_url=url, library_id=entry['id'], arrangement_source_url=entry['source_url'],
                  arrangement_source_name=entry['source_name'], arrangement_kind='melody',
                  source_notes='Упрощённая аранжировка из существующего MIDI-источника.',
                  lyrics_notice='Мелодия и простой бас–аккорд из нотного источника. Тональность и темп могут отличаться от видео.')
    return result
