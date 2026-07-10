"""进程内节点编辑锁，替代独立部署时的 Redis 锁。

桌面集成场景下服务是单进程 uvicorn（含局域网协作也只有这一个进程），
因此内存字典 + TTL 过期即可提供与原 Redis SET NX EX 等价的语义。
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass


@dataclass
class LockEntry:
    user_id: str
    username: str
    locked_at: str  # ISO 时间，仅用于展示
    expires_at: float  # time.monotonic() 截止时间


_locks: dict[tuple[str, str], LockEntry] = {}  # (map_id, node_id) -> entry
_guard = threading.Lock()


def _purge_expired(now: float) -> None:
    expired = [k for k, v in _locks.items() if v.expires_at <= now]
    for k in expired:
        del _locks[k]


def try_acquire(map_id: str, node_id: str, user_id: str, username: str,
                locked_at: str, ttl: int) -> LockEntry | None:
    """成功（新获取或本人续期）返回锁条目；被他人持有返回持有者条目。"""
    now = time.monotonic()
    with _guard:
        _purge_expired(now)
        key = (map_id, node_id)
        existing = _locks.get(key)
        if existing is not None and existing.user_id != user_id:
            return existing
        # 新锁或本人续期（续期保留原 locked_at 便于展示持锁起始时间）
        entry = LockEntry(
            user_id=user_id,
            username=username,
            locked_at=existing.locked_at if existing else locked_at,
            expires_at=now + ttl,
        )
        _locks[key] = entry
        return entry


def release(map_id: str, node_id: str, user_id: str) -> bool:
    with _guard:
        key = (map_id, node_id)
        existing = _locks.get(key)
        if existing is not None and existing.user_id == user_id:
            del _locks[key]
            return True
        return False


def get_map_locks(map_id: str) -> list[dict]:
    now = time.monotonic()
    with _guard:
        _purge_expired(now)
        return [
            {
                "node_id": node_id,
                "map_id": mid,
                "user_id": entry.user_id,
                "username": entry.username,
                "locked_at": entry.locked_at,
            }
            for (mid, node_id), entry in _locks.items()
            if mid == map_id
        ]


def get_owner(map_id: str, node_id: str) -> LockEntry | None:
    now = time.monotonic()
    with _guard:
        _purge_expired(now)
        return _locks.get((map_id, node_id))
