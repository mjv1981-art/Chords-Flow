"""Local checkpoints for validated scores; no API keys or provider responses."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time


class ScoreCache:
    def __init__(self, url):
        folder = Path(os.environ.get('BAYANFLOW_CACHE_DIR', str(Path(tempfile.gettempdir()) / 'bayanflow-transcriptions')))
        folder.mkdir(mode=0o700, parents=True, exist_ok=True)
        database = folder / 'scores.sqlite3'
        self.connection = sqlite3.connect(database, timeout=10)
        database.chmod(0o600)
        self.connection.execute('CREATE TABLE IF NOT EXISTS scores (id TEXT PRIMARY KEY, data TEXT NOT NULL, saved REAL NOT NULL)')
        self.connection.execute('DELETE FROM scores WHERE saved < ?', (time.time() - 7 * 86400,))
        self.connection.commit()
        self.namespace = [url, os.environ.get('GEMINI_MODEL', 'gemini-3.8-flash'), 'score-v2']

    def key(self, *parts):
        return hashlib.sha256(json.dumps(self.namespace + list(parts), sort_keys=True).encode()).hexdigest()

    def get(self, key):
        row = self.connection.execute('SELECT data FROM scores WHERE id = ?', (key,)).fetchone()
        return row[0] if row else None

    def put(self, key, model):
        self.connection.execute('INSERT OR REPLACE INTO scores VALUES (?, ?, ?)', (key, model.model_dump_json(), time.time()))
        self.connection.commit()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.connection.close()
