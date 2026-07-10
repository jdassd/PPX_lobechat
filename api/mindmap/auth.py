from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from api.mindmap.config import load_config

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"


def _get_secret() -> str:
    return load_config().jwt_secret


def _get_config():
    return load_config()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str, username: str) -> str:
    config = _get_config()
    expire = datetime.now(timezone.utc) + timedelta(minutes=config.access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "username": username,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, config.jwt_secret, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> tuple[str, datetime]:
    config = _get_config()
    expire = datetime.now(timezone.utc) + timedelta(days=config.refresh_token_expire_days)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
    }
    token = jwt.encode(payload, config.jwt_secret, algorithm=ALGORITHM)
    return token, expire


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, _get_secret(), algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from api.mindmap.db import get_db
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id, username, email, display_name FROM users WHERE id = ?", (payload["sub"],))
        user = await cursor.fetchone()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return dict(user)
    finally:
        await db.close()


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict | None:
    """Like get_current_user but returns None instead of 401 if not authenticated."""
    if credentials is None:
        return None
    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        return None

    from api.mindmap.db import get_db
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id, username, email, display_name FROM users WHERE id = ?", (payload["sub"],))
        user = await cursor.fetchone()
        return dict(user) if user else None
    finally:
        await db.close()
