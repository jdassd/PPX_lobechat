from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.mindmap.auth import get_current_user
from api.mindmap.services import map_service, node_service, permission_service

router = APIRouter(prefix="/api/maps", tags=["maps"])


class CreateMapRequest(BaseModel):
    name: str
    team_id: Optional[str] = None


class ClaimMapRequest(BaseModel):
    pass


@router.get("")
async def list_maps(user: dict = Depends(get_current_user)):
    return await map_service.list_maps(user["id"])


@router.post("", status_code=201)
async def create_map(req: CreateMapRequest, user: dict = Depends(get_current_user)):
    # If team_id provided, check user has edit permission on that team
    if req.team_id:
        if not await permission_service.check_team_access(user["id"], req.team_id, "edit"):
            raise HTTPException(status_code=403, detail="No edit access to this team")
    return await map_service.create_map(req.name, owner_id=user["id"], team_id=req.team_id)


@router.get("/{map_id}")
async def get_map(map_id: str, user: dict = Depends(get_current_user)):
    if not await permission_service.check_map_access(user["id"], map_id, "view"):
        raise HTTPException(status_code=403, detail="Access denied")
    result = await map_service.get_map_with_nodes(map_id)
    if not result:
        raise HTTPException(status_code=404, detail="Map not found")
    return result


@router.get("/{map_id}/sync")
async def sync_map(map_id: str, since: int = 0, user: dict = Depends(get_current_user)):
    if not await permission_service.check_map_access(user["id"], map_id, "view"):
        raise HTTPException(status_code=403, detail="Access denied")
    result = await map_service.get_sync(map_id, since)
    if result is None:
        raise HTTPException(status_code=404, detail="Map not found")
    return result


@router.delete("/{map_id}", status_code=204)
async def delete_map(map_id: str, user: dict = Depends(get_current_user)):
    if not await permission_service.check_map_access(user["id"], map_id, "owner"):
        raise HTTPException(status_code=403, detail="Only the owner can delete this map")
    deleted = await map_service.delete_map(map_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Map not found")


@router.post("/{map_id}/claim")
async def claim_map(map_id: str, user: dict = Depends(get_current_user)):
    """Claim a legacy map (owner_id=NULL) for the current user."""
    result = await map_service.claim_map(map_id, user["id"])
    if result is None:
        raise HTTPException(status_code=404, detail="Map not found")
    if result is False:
        raise HTTPException(status_code=409, detail="Map already has an owner")
    return result


@router.get("/{map_id}/history")
async def get_map_history(map_id: str, user: dict = Depends(get_current_user)):
    if not await permission_service.check_map_access(user["id"], map_id, "view"):
        raise HTTPException(status_code=403, detail="Access denied")
    return await node_service.get_map_history(map_id)
