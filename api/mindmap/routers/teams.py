from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.mindmap.auth import get_current_user
from api.mindmap.services import permission_service, team_service

router = APIRouter(prefix="/api", tags=["teams"])


class CreateTeamRequest(BaseModel):
    name: str


class UpdateTeamRequest(BaseModel):
    name: str


class AddMemberRequest(BaseModel):
    email: str
    role: str = "viewer"


class UpdateMemberRequest(BaseModel):
    role: str


class InviteRequest(BaseModel):
    email: str
    role: str = "viewer"


# --- Team CRUD ---

@router.post("/teams", status_code=201)
async def create_team(req: CreateTeamRequest, user: dict = Depends(get_current_user)):
    return await team_service.create_team(req.name, user["id"])


@router.get("/teams")
async def list_teams(user: dict = Depends(get_current_user)):
    return await team_service.list_user_teams(user["id"])


@router.get("/teams/{team_id}")
async def get_team(team_id: str, user: dict = Depends(get_current_user)):
    if not await permission_service.check_team_access(user["id"], team_id, "view"):
        raise HTTPException(status_code=403, detail="Access denied")
    team = await team_service.get_team(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.put("/teams/{team_id}")
async def update_team(team_id: str, req: UpdateTeamRequest, user: dict = Depends(get_current_user)):
    if not await permission_service.check_team_access(user["id"], team_id, "admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    result = await team_service.update_team(team_id, req.name)
    if not result:
        raise HTTPException(status_code=404, detail="Team not found")
    return result


@router.delete("/teams/{team_id}", status_code=204)
async def delete_team(team_id: str, user: dict = Depends(get_current_user)):
    if not await permission_service.check_team_access(user["id"], team_id, "owner"):
        raise HTTPException(status_code=403, detail="Only the owner can delete the team")
    deleted = await team_service.delete_team(team_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Team not found")


# --- Members ---

@router.get("/teams/{team_id}/members")
async def list_members(team_id: str, user: dict = Depends(get_current_user)):
    if not await permission_service.check_team_access(user["id"], team_id, "view"):
        raise HTTPException(status_code=403, detail="Access denied")
    return await team_service.list_team_members(team_id)


@router.post("/teams/{team_id}/members", status_code=201)
async def invite_member(team_id: str, req: InviteRequest, user: dict = Depends(get_current_user)):
    if not await permission_service.check_team_access(user["id"], team_id, "admin"):
        raise HTTPException(status_code=403, detail="Only admins and above can invite members")
    if req.role not in ("admin", "editor", "viewer"):
        raise HTTPException(status_code=400, detail="Invalid role")
    result = await team_service.create_invitation(team_id, user["id"], req.email, req.role)
    if "error" in result:
        raise HTTPException(status_code=409, detail=result["error"])
    return result


@router.put("/teams/{team_id}/members/{member_id}")
async def update_member(team_id: str, member_id: str, req: UpdateMemberRequest, user: dict = Depends(get_current_user)):
    if not await permission_service.check_team_access(user["id"], team_id, "admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    if req.role not in ("admin", "editor", "viewer"):
        raise HTTPException(status_code=400, detail="Invalid role. Cannot set to owner.")
    updated = await team_service.update_member_role(team_id, member_id, req.role)
    if not updated:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"team_id": team_id, "user_id": member_id, "role": req.role}


@router.delete("/teams/{team_id}/members/{member_id}", status_code=204)
async def remove_member(team_id: str, member_id: str, user: dict = Depends(get_current_user)):
    if not await permission_service.check_team_access(user["id"], team_id, "admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    removed = await team_service.remove_team_member(team_id, member_id)
    if not removed:
        raise HTTPException(status_code=400, detail="Cannot remove member (may be the owner)")


# --- Invitations ---

@router.get("/invitations")
async def list_invitations(user: dict = Depends(get_current_user)):
    return await team_service.list_user_invitations(user["email"])


@router.post("/invitations/{invitation_id}/accept")
async def accept_invitation(invitation_id: str, user: dict = Depends(get_current_user)):
    result = await team_service.accept_invitation(invitation_id, user["id"])
    if not result:
        raise HTTPException(status_code=404, detail="Invitation not found or already processed")
    return result


@router.post("/invitations/{invitation_id}/decline")
async def decline_invitation(invitation_id: str, user: dict = Depends(get_current_user)):
    result = await team_service.decline_invitation(invitation_id, user["id"])
    if not result:
        raise HTTPException(status_code=404, detail="Invitation not found or already processed")
    return result
