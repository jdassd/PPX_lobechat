"""Versioned SQLite records; imports legacy JSON once without deleting it."""
from __future__ import annotations

import json
import shutil
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from api.core.database import migrate_database


def _create_records(connection):
    connection.execute('CREATE TABLE IF NOT EXISTS state_meta (namespace TEXT PRIMARY KEY, payload TEXT NOT NULL)')
    connection.execute('CREATE TABLE IF NOT EXISTS state_records (namespace TEXT, collection TEXT, id TEXT, position INTEGER NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(namespace, collection, id))')


def _index_records(connection):
    connection.execute('CREATE INDEX IF NOT EXISTS state_record_order ON state_records(namespace, collection, position)')


class StateStore:
    def __init__(self, root):
        self.path = Path(root) / 'workbench.sqlite3'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.upgrade_backup = migrate_database(self.path, {1: _create_records, 2: _index_records})

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=30)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def load(self, namespace, legacy_path, default):
        with self.connect() as connection:
            row = connection.execute('SELECT payload FROM state_meta WHERE namespace=?', (namespace,)).fetchone()
            if row:
                result = json.loads(row[0])
                collections = result.pop('_collections', [])
                for collection in collections:
                    result[collection] = [json.loads(record[0]) for record in connection.execute(
                        'SELECT payload FROM state_records WHERE namespace=? AND collection=? ORDER BY position', (namespace, collection))]
                return result
        legacy = Path(legacy_path)
        payload = default
        candidates = [legacy, legacy.with_suffix('.bak')]
        errors = []
        for candidate in candidates:
            if not candidate.exists():
                continue
            try:
                payload = json.loads(candidate.read_text(encoding='utf-8-sig'))
                if not isinstance(payload, dict):
                    raise ValueError('记录根节点必须为对象')
                backup = candidate.with_name(candidate.name + '.pre-sqlite.bak')
                if not backup.exists():
                    shutil.copy2(candidate, backup)
                break
            except (OSError, ValueError) as exc:
                errors.append(str(exc))
        else:
            if errors:
                raise ValueError('旧记录损坏，已保留原文件：' + '; '.join(errors))
        self.save(namespace, payload)
        return payload

    def save(self, namespace, payload):
        collections = {key: value for key, value in payload.items() if isinstance(value, list)}
        metadata = {key: value for key, value in payload.items() if key not in collections}
        metadata['_collections'] = list(collections)
        with self.connect() as connection:
            connection.execute('INSERT OR REPLACE INTO state_meta VALUES (?, ?)',
                               (namespace, json.dumps(metadata, ensure_ascii=False)))
            for collection, items in collections.items():
                previous = {row[0]: (row[1], row[2]) for row in connection.execute(
                    'SELECT id, position, payload FROM state_records WHERE namespace=? AND collection=?', (namespace, collection))}
                seen = set()
                for position, item in enumerate(items):
                    identity = str(item.get('id') or position) if isinstance(item, dict) else str(position)
                    seen.add(identity)
                    encoded = json.dumps(item, ensure_ascii=False)
                    if previous.get(identity) != (position, encoded):
                        connection.execute('INSERT OR REPLACE INTO state_records VALUES (?, ?, ?, ?, ?)',
                                           (namespace, collection, identity, position, encoded))
                connection.executemany('DELETE FROM state_records WHERE namespace=? AND collection=? AND id=?',
                                       [(namespace, collection, identity) for identity in previous.keys() - seen])

    def backup(self, target):
        with self.connect() as source:
            destination = sqlite3.connect(target)
            try:
                source.backup(destination)
            finally:
                destination.close()
