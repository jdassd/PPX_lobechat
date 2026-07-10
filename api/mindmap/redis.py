"""进程内 Redis 替身（仅覆盖 node_locks 用到的命令子集）。

桌面内嵌场景没有外部 Redis，节点锁改用进程内存实现：
  - 字符串键值 + 秒级 TTL（读取时惰性过期）
  - SET 集合（sadd/srem/smembers，无 TTL）
  - 单事件循环内各方法无 await 切换点，操作天然原子

保持与 redis.asyncio 客户端（decode_responses=True）相同的调用签名，
routers/node_locks.py 无需任何改动。
"""

import time
from typing import Optional


class InMemoryRedis:
    """异步接口的进程内 KV 存储。"""

    def __init__(self):
        # key -> (value: str, expire_at: float | None)
        self._strings: dict = {}
        # key -> set[str]
        self._sets: dict = {}

    def _purge_if_expired(self, key: str) -> None:
        item = self._strings.get(key)
        if item is not None and item[1] is not None and item[1] <= time.monotonic():
            del self._strings[key]

    async def set(self, key, value, ex=None):
        expire_at = time.monotonic() + ex if ex is not None else None
        self._strings[str(key)] = (str(value), expire_at)
        return True

    async def get(self, key) -> Optional[str]:
        key = str(key)
        self._purge_if_expired(key)
        item = self._strings.get(key)
        return item[0] if item is not None else None

    async def expire(self, key, ttl) -> bool:
        key = str(key)
        self._purge_if_expired(key)
        item = self._strings.get(key)
        if item is None:
            return False
        self._strings[key] = (item[0], time.monotonic() + ttl)
        return True

    async def delete(self, *keys) -> int:
        count = 0
        for key in keys:
            key = str(key)
            self._purge_if_expired(key)
            if self._strings.pop(key, None) is not None:
                count += 1
            if self._sets.pop(key, None) is not None:
                count += 1
        return count

    async def sadd(self, key, *members) -> int:
        target = self._sets.setdefault(str(key), set())
        added = 0
        for member in members:
            member = str(member)
            if member not in target:
                target.add(member)
                added += 1
        return added

    async def srem(self, key, *members) -> int:
        key = str(key)
        target = self._sets.get(key)
        if not target:
            return 0
        removed = 0
        for member in members:
            member = str(member)
            if member in target:
                target.discard(member)
                removed += 1
        if not target:
            self._sets.pop(key, None)
        return removed

    async def smembers(self, key) -> set:
        return set(self._sets.get(str(key), set()))

    async def close(self):
        self._strings.clear()
        self._sets.clear()


_redis: Optional[InMemoryRedis] = None


async def get_redis() -> InMemoryRedis:
    global _redis
    if _redis is None:
        _redis = InMemoryRedis()
    return _redis


async def close_redis():
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None
