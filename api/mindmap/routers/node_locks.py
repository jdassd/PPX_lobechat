import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.mindmap.database import get_db
from api.mindmap.middleware.auth import get_current_user
from api.mindmap.models.mind_map import MindMap
from api.mindmap.models.user import User
from api.mindmap.redis import get_redis
from api.mindmap.services.mind_map import can_access_mindmap

router = APIRouter(prefix="/api/mindmaps", tags=["node-locks"])

LOCK_TTL = 60  # seconds, auto-expire if not refreshed


def _lock_key(mindmap_id: str, node_uid: str) -> str:
    return f"node_lock:{mindmap_id}:{node_uid}"


def _index_key(mindmap_id: str) -> str:
    return f"node_locks_index:{mindmap_id}"


class LockResponse(BaseModel):
    node_uid: str
    user_id: str
    display_name: str


class LockRequest(BaseModel):
    node_uid: str


@router.get("/{mindmap_id}/locks")
async def get_locks(
    mindmap_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all current locks for a mindmap, plus the mindmap's updated_at for data sync."""
    result = await db.execute(select(MindMap).where(MindMap.id == mindmap_id))
    mindmap = result.scalar_one_or_none()
    if not mindmap:
        raise HTTPException(status_code=404, detail="Mind map not found")
    role = await can_access_mindmap(db, current_user.id, mindmap)
    if role is None:
        raise HTTPException(status_code=403, detail="Access denied")

    r = await get_redis()
    index_key = _index_key(mindmap_id)
    node_uids = await r.smembers(index_key)

    locks = []
    expired = []
    for node_uid in node_uids:
        val = await r.get(_lock_key(mindmap_id, node_uid))
        if val:
            info = json.loads(val)
            locks.append({
                "node_uid": node_uid,
                "user_id": info["user_id"],
                "display_name": info["display_name"],
            })
        else:
            expired.append(node_uid)

    # Clean up expired entries from the index
    if expired:
        await r.srem(index_key, *expired)

    return {
        "locks": locks,
        "updated_at": mindmap.updated_at.isoformat() if mindmap.updated_at else None
    }


@router.post("/{mindmap_id}/locks")
async def lock_node(
    mindmap_id: str,
    body: LockRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lock a node for editing. Returns success or the current lock holder."""
    result = await db.execute(select(MindMap).where(MindMap.id == mindmap_id))
    mindmap = result.scalar_one_or_none()
    if not mindmap:
        raise HTTPException(status_code=404, detail="Mind map not found")
    role = await can_access_mindmap(db, current_user.id, mindmap)
    if role is None:
        raise HTTPException(status_code=403, detail="Access denied")
    if role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot edit")

    r = await get_redis()
    key = _lock_key(mindmap_id, body.node_uid)
    existing = await r.get(key)

    if existing:
        info = json.loads(existing)
        if info["user_id"] != current_user.id:
            return {
                "success": False,
                "locked_by": {
                    "user_id": info["user_id"],
                    "display_name": info["display_name"],
                }
            }
        # Same user re-locking: refresh TTL
        await r.expire(key, LOCK_TTL)
        return {"success": True}

    lock_data = json.dumps({
        "user_id": current_user.id,
        "display_name": current_user.display_name,
    })
    await r.set(key, lock_data, ex=LOCK_TTL)
    await r.sadd(_index_key(mindmap_id), body.node_uid)
    return {"success": True}


@router.delete("/{mindmap_id}/locks/{node_uid}")
async def unlock_node(
    mindmap_id: str,
    node_uid: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unlock a node."""
    r = await get_redis()
    key = _lock_key(mindmap_id, node_uid)
    existing = await r.get(key)

    if existing:
        info = json.loads(existing)
        if info["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Cannot unlock another user's lock")
        await r.delete(key)
        await r.srem(_index_key(mindmap_id), node_uid)

    return {"success": True}


@router.post("/{mindmap_id}/locks/{node_uid}/refresh")
async def refresh_lock(
    mindmap_id: str,
    node_uid: str,
    current_user: User = Depends(get_current_user),
):
    """Refresh the TTL of an existing lock."""
    r = await get_redis()
    key = _lock_key(mindmap_id, node_uid)
    existing = await r.get(key)

    if not existing:
        return {"success": False, "reason": "lock_expired"}

    info = json.loads(existing)
    if info["user_id"] != current_user.id:
        return {"success": False, "reason": "not_owner"}

    await r.expire(key, LOCK_TTL)
    return {"success": True}
