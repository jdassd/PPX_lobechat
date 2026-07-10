from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from api.mindmap.auth import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from api.mindmap.db import get_db


async def register_user(username: str, email: str, password: str, display_name: str = "") -> dict:
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    password_hash = hash_password(password)
    if not display_name:
        display_name = username

    db = await get_db()
    try:
        # Check uniqueness
        cursor = await db.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
        existing = await cursor.fetchone()
        if existing:
            return {"error": "Username or email already exists"}

        await db.execute(
            "INSERT INTO users (id, username, email, password_hash, display_name, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, username, email, password_hash, display_name, now, now),
        )
        await db.commit()
        return {
            "id": user_id,
            "username": username,
            "email": email,
            "display_name": display_name,
        }
    finally:
        await db.close()


async def authenticate_user(username: str, password: str) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, username, email, password_hash, display_name FROM users WHERE username = ?",
            (username,),
        )
        user = await cursor.fetchone()
        if not user:
            return None
        if not verify_password(password, user["password_hash"]):
            return None
        return {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "display_name": user["display_name"],
        }
    finally:
        await db.close()


async def store_refresh_token(user_id: str, token: str, expires_at: datetime) -> None:
    token_id = str(uuid.uuid4())
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at) VALUES (?, ?, ?, ?)",
            (token_id, user_id, token_hash, expires_at.isoformat()),
        )
        await db.commit()
    finally:
        await db.close()


async def validate_refresh_token(token: str) -> dict | None:
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        return None

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT rt.id, rt.user_id, u.username, u.email, u.display_name FROM refresh_tokens rt JOIN users u ON rt.user_id = u.id WHERE rt.token_hash = ? AND rt.expires_at > ?",
            (token_hash, datetime.now(timezone.utc).isoformat()),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return {
            "token_id": row["id"],
            "user_id": row["user_id"],
            "username": row["username"],
            "email": row["email"],
            "display_name": row["display_name"],
        }
    finally:
        await db.close()


async def revoke_refresh_token(token: str) -> None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    db = await get_db()
    try:
        await db.execute("DELETE FROM refresh_tokens WHERE token_hash = ?", (token_hash,))
        await db.commit()
    finally:
        await db.close()


async def revoke_all_refresh_tokens(user_id: str) -> None:
    db = await get_db()
    try:
        await db.execute("DELETE FROM refresh_tokens WHERE user_id = ?", (user_id,))
        await db.commit()
    finally:
        await db.close()
