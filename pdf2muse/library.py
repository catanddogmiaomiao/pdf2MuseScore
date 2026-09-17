"""Local score ownership and version history; no score content is modified."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sqlite3
import uuid
from datetime import datetime
from contextlib import contextmanager


class ScoreLibrary:
    def __init__(self, root=None):
        self.root = Path(root) if root else Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'PDF2Muse' / 'library'

    @contextmanager
    def _connect(self):
        self.root.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.root / 'library.sqlite3')
        try:
            with connection:
                connection.execute('CREATE TABLE IF NOT EXISTS scores (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
                yield connection
        finally:
            connection.close()

    def entries(self):
        if not (self.root / 'library.sqlite3').exists():
            return []
        with self._connect() as connection:
            items = [json.loads(row[0]) for row in connection.execute('SELECT data FROM scores')]
        return sorted(items, key=lambda item: item['updated'], reverse=True)

    def save(self, item):
        item = dict(item, updated=datetime.now().isoformat(timespec='seconds'))
        with self._connect() as connection:
            connection.execute('INSERT OR REPLACE INTO scores VALUES (?, ?)', (item['id'], json.dumps(item, ensure_ascii=False)))
        return item

    def import_pdf(self, source, pages):
        source = Path(source)
        digest = self._digest(source)
        for item in self.entries():
            if item['digest'] == digest and Path(item['pdf']).is_file():
                return item
        identifier = uuid.uuid4().hex
        directory = self.root / 'scores' / identifier
        directory.mkdir(parents=True)
        try:
            target = directory / source.name
            shutil.copy2(source, target)
            return self.save(dict(id=identifier, title=source.stem, digest=digest,
                                  pdf=str(target), source=str(source), pages=pages,
                                  versions=[], edited=None, state='new'))
        except Exception:
            shutil.rmtree(directory)
            raise

    @staticmethod
    def _digest(source):
        digest = hashlib.sha256()
        with source.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        return digest.hexdigest()

    def add_result(self, item, result):
        item = next((entry for entry in self.entries() if entry['id'] == item['id']), item)
        directory = Path(item['pdf']).parent / 'versions' / uuid.uuid4().hex
        directory.mkdir(parents=True)
        try:
            target = directory / result.output.name
            shutil.copy2(result.output, target)
            log = directory / 'homr.log'
            shutil.copy2(result.log_file, log)
            version = dict(path=str(target), log=str(log), created=datetime.now().isoformat(timespec='seconds'))
            return self.save(dict(item, versions=[version, *item['versions']], state='ready'))
        except Exception:
            shutil.rmtree(directory)
            raise

    def remove(self, identifier):
        # Keep owned PDFs and outputs on disk; removing a list entry is reversible.
        with self._connect() as connection:
            connection.execute('DELETE FROM scores WHERE id=?', (identifier,))
