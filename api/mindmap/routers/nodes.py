from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.mindmap.auth import get_current_user
from api.mindmap.services import node_service, permission_service

router = APIRouter(prefix="/api/maps/{map_id}/nodes", tags=["nodes"])


class CreateNodeRequest(BaseModel):
    parent_id: str
    content: str = ""
    position: int = 0
    style: str = "{}"
    id: Optional[str] = None


class UpdateNodeRequest(BaseModel):
    content: Optional[str] = None
    position: Optional[int] = None
    style: Optional[str] = None
    collapsed: Optional[bool] = None
    parent_id: Optional[str] = None


@router.post("", status_code=201)
async def create_node(map_id: str, req: CreateNodeRequest, user: dict = Depends(get_current_user)):
    if not await permission_service.check_map_access(user["id"], map_id, "edit"):
        raise HTTPException(status_code=403, detail="No edit access")
    result = await node_service.create_node(
        map_id=map_id,
        parent_id=req.parent_id,
        content=req.content,
        position=req.position,
        style=req.style,
        node_id=req.id,
        user_id=user["id"],
        username=user.get("username", ""),
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Parent node not found in this map")
    return result


@router.put("/{node_id}")
async def update_node(map_id: str, node_id: str, req: UpdateNodeRequest, user: dict = Depends(get_current_user)):
    if not await permission_service.check_map_access(user["id"], map_id, "edit"):
        raise HTTPException(status_code=403, detail="No edit access")
    changes = {k: v for k, v in req.model_dump().items() if v is not None}
    if not changes:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    result = await node_service.update_node(map_id, node_id, changes, user_id=user["id"], username=user.get("username", ""))
    if not result:
        raise HTTPException(status_code=404, detail="Node not found")
    if isinstance(result, dict) and result.get("lock_conflict"):
        raise HTTPException(
            status_code=409,
            detail=f"{result['locked_by']} 正在编辑该节点，请等待操作结束后再进行操作",
        )
    return result


@router.delete("/{node_id}")
async def delete_node(map_id: str, node_id: str, user: dict = Depends(get_current_user)):
    if not await permission_service.check_map_access(user["id"], map_id, "edit"):
        raise HTTPException(status_code=403, detail="No edit access")
    result = await node_service.delete_node(map_id, node_id, user_id=user["id"], username=user.get("username", ""))
    if not result:
        raise HTTPException(status_code=404, detail="Node not found")
    if isinstance(result, dict) and result.get("lock_conflict"):
        raise HTTPException(
            status_code=409,
            detail=f"{result['locked_by']} 正在编辑该节点，请等待操作结束后再进行操作",
        )
    return result


@router.get("/{node_id}/history")
async def get_node_history(map_id: str, node_id: str, user: dict = Depends(get_current_user)):
    if not await permission_service.check_map_access(user["id"], map_id, "view"):
        raise HTTPException(status_code=403, detail="Access denied")
    if not await node_service.node_belongs_to_map(node_id, map_id):
        raise HTTPException(status_code=404, detail="Node not found")
    return await node_service.get_node_history(node_id)


@router.post("/{node_id}/history/{history_id}/rollback")
async def rollback_node_history(
    map_id: str, node_id: str, history_id: int, user: dict = Depends(get_current_user)
):
    if not await permission_service.check_map_access(user["id"], map_id, "edit"):
        raise HTTPException(status_code=403, detail="No edit access")
    result = await node_service.rollback_to_history(
        history_id=history_id,
        map_id=map_id,
        user_id=user["id"],
        username=user.get("username", ""),
        expected_node_id=node_id,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/{node_id}/lock")
async def lock_node(map_id: str, node_id: str, user: dict = Depends(get_current_user)):
    if not await permission_service.check_map_access(user["id"], map_id, "edit"):
        raise HTTPException(status_code=403, detail="No edit access")
    if not await node_service.node_belongs_to_map(node_id, map_id):
        raise HTTPException(status_code=404, detail="Node not found")
    result = await node_service.acquire_lock(node_id, map_id, user["id"], user.get("username", ""))
    if result.get("locked") is False:
        raise HTTPException(
            status_code=409,
            detail=f"{result['locked_by']} 正在编辑该节点，请等待操作结束后再进行操作",
        )
    return result


@router.delete("/{node_id}/lock")
async def unlock_node(map_id: str, node_id: str, user: dict = Depends(get_current_user)):
    if not await permission_service.check_map_access(user["id"], map_id, "edit"):
        raise HTTPException(status_code=403, detail="No edit access")
    if not await node_service.node_belongs_to_map(node_id, map_id):
        raise HTTPException(status_code=404, detail="Node not found")
    await node_service.release_lock(node_id, map_id, user["id"])
    return {"status": "ok"}
