from __future__ import annotations

import aiosqlite

_db_path: str = ""


def set_db_path(path: str) -> None:
    global _db_path
    _db_path = path


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(_db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db() -> None:
    db = await get_db()
    try:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS maps (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                version     INTEGER NOT NULL DEFAULT 0,
                owner_id    TEXT,
                team_id     TEXT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS nodes (
                id          TEXT PRIMARY KEY,
                map_id      TEXT NOT NULL REFERENCES maps(id) ON DELETE CASCADE,
                parent_id   TEXT REFERENCES nodes(id) ON DELETE CASCADE,
                content     TEXT NOT NULL DEFAULT '',
                position    INTEGER NOT NULL DEFAULT 0,
                style       TEXT DEFAULT '{}',
                collapsed   BOOLEAN DEFAULT 0,
                version     INTEGER NOT NULL DEFAULT 0,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_nodes_map ON nodes(map_id);
            CREATE INDEX IF NOT EXISTS idx_nodes_parent ON nodes(parent_id);

            CREATE TABLE IF NOT EXISTS change_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                map_id      TEXT NOT NULL REFERENCES maps(id) ON DELETE CASCADE,
                version     INTEGER NOT NULL,
                action      TEXT NOT NULL,
                node_id     TEXT NOT NULL,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_changelog_map_ver ON change_log(map_id, version);

            -- Auth tables
            CREATE TABLE IF NOT EXISTS users (
                id            TEXT PRIMARY KEY,
                username      TEXT NOT NULL UNIQUE,
                email         TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                display_name  TEXT NOT NULL DEFAULT '',
                created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id          TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token_hash  TEXT NOT NULL,
                expires_at  DATETIME NOT NULL,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);

            -- Team tables
            CREATE TABLE IF NOT EXISTS teams (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                owner_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS team_members (
                team_id     TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
                user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                role        TEXT NOT NULL DEFAULT 'viewer' CHECK(role IN ('owner','admin','editor','viewer')),
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (team_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS team_invitations (
                id            TEXT PRIMARY KEY,
                team_id       TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
                inviter_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                invitee_email TEXT NOT NULL,
                role          TEXT NOT NULL DEFAULT 'viewer' CHECK(role IN ('admin','editor','viewer')),
                status        TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','accepted','declined')),
                created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_invitations_email ON team_invitations(invitee_email);
            CREATE INDEX IF NOT EXISTS idx_maps_owner ON maps(owner_id);
            CREATE INDEX IF NOT EXISTS idx_maps_team ON maps(team_id);

            CREATE TABLE IF NOT EXISTS node_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id     TEXT NOT NULL,
                map_id      TEXT NOT NULL,
                user_id     TEXT,
                username    TEXT DEFAULT '',
                action      TEXT NOT NULL CHECK(action IN ('create','update','delete')),
                old_content TEXT,
                new_content TEXT,
                old_parent_id TEXT,
                new_parent_id TEXT,
                old_position INTEGER,
                new_position INTEGER,
                snapshot    TEXT,
                map_version INTEGER,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_node_history_node ON node_history(node_id);
            CREATE INDEX IF NOT EXISTS idx_node_history_map ON node_history(map_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS node_locks (
                node_id     TEXT PRIMARY KEY,
                map_id      TEXT NOT NULL,
                user_id     TEXT NOT NULL,
                username    TEXT DEFAULT '',
                locked_at   DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        # Migrate: add version column to existing tables if missing
        try:
            await db.execute("ALTER TABLE maps ADD COLUMN version INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE nodes ADD COLUMN version INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass
        # Migrate: add owner_id/team_id to maps if missing
        try:
            await db.execute("ALTER TABLE maps ADD COLUMN owner_id TEXT")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE maps ADD COLUMN team_id TEXT")
        except Exception:
            pass
        # Migrate: add last_edited_by fields to nodes if missing
        try:
            await db.execute("ALTER TABLE nodes ADD COLUMN last_edited_by TEXT")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE nodes ADD COLUMN last_edited_by_name TEXT DEFAULT ''")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE nodes ADD COLUMN last_edited_at DATETIME")
        except Exception:
            pass
        await db.commit()
    finally:
        await db.close()
