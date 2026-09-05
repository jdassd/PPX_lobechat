"""Transactional SQLite schema upgrades with a consistent pre-upgrade snapshot."""
from __future__ import annotations

import os
import sqlite3
import time
import uuid
from contextlib import closing
from pathlib import Path


def migrate_database(path, migrations):
    """Each migration receives a connection; it must not commit or use executescript."""
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    target_version = max(migrations, default=0)
    connection = sqlite3.connect(path, timeout=30, isolation_level=None)
    backup_path = None
    temporary = None
    try:
        connection.execute('BEGIN IMMEDIATE')
        version = connection.execute('PRAGMA user_version').fetchone()[0]
        if version > target_version:
            raise ValueError('数据库来自更新版本，请使用相应版本打开或从升级前备份恢复')
        has_data = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' LIMIT 1").fetchone()
        if version < target_version and has_data:
            directory = path.parent / 'upgrade-backups'
            directory.mkdir(exist_ok=True)
            backup_path = directory / f'{path.name}.v{version}.{time.time_ns()}.{uuid.uuid4().hex[:8]}.sqlite3'
            temporary = backup_path.with_suffix('.tmp')
            # The reserved write lock prevents another migration/writer; this separate
            # read connection includes committed WAL pages without backing up our lock.
            with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=30)) as source, closing(sqlite3.connect(temporary)) as destination:
                source.backup(destination)
                if destination.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                    raise ValueError('升级前数据库备份未通过一致性检查')
            os.replace(temporary, backup_path)
        for next_version in range(version + 1, target_version + 1):
            if next_version not in migrations:
                raise ValueError(f'缺少数据库迁移步骤：{next_version}')
            migrations[next_version](connection)
            connection.execute(f'PRAGMA user_version={next_version}')
        connection.commit()
        connection.execute('PRAGMA journal_mode=WAL')
        return str(backup_path) if backup_path else None
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
        if temporary is not None:
            temporary.unlink(missing_ok=True)
