from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.mindmap.database import get_db
from api.mindmap.middleware.auth import get_current_user
from api.mindmap.models.invitation import TeamInvitation
from api.mindmap.models.mind_map import MindMap
from api.mindmap.models.team import Team, TeamMember
from api.mindmap.models.user import User
from api.mindmap.schemas.mind_map import MindMapCreate, MindMapListItem, MindMapResponse
from api.mindmap.schemas.team import (
    InviteRequest,
    TeamCreate,
    TeamDetailResponse,
    TeamMemberResponse,
    TeamResponse,
    TeamUpdate,
    UpdateMemberRoleRequest,
)
from api.mindmap.services.mind_map import get_team_mindmaps
from api.mindmap.services.team import get_member_role, get_user_teams, require_role

router = APIRouter(prefix="/api/teams", tags=["teams"])


@router.get("", response_model=list[TeamResponse])
async def list_teams(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    teams_data = await get_user_teams(db, current_user.id)
    return [t["team"] for t in teams_data]


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    body: TeamCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    team = Team(name=body.name, description=body.description, owner_id=current_user.id)
    db.add(team)
    await db.flush()
    member = TeamMember(team_id=team.id, user_id=current_user.id, role="owner")
    db.add(member)
    await db.commit()
    await db.refresh(team)
    return team


@router.get("/{team_id}", response_model=TeamDetailResponse)
async def get_team(
    team_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    role = await get_member_role(db, team_id, current_user.id)
    if role is None:
        raise HTTPException(status_code=403, detail="Not a member")
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    members_result = await db.execute(
        select(TeamMember, User)
        .join(User, TeamMember.user_id == User.id)
        .where(TeamMember.team_id == team_id)
    )
    members = [
        TeamMemberResponse(
            id=tm.id, user_id=tm.user_id, email=u.email,
            display_name=u.display_name, role=tm.role, joined_at=tm.joined_at,
        )
        for tm, u in members_result.all()
    ]
    return TeamDetailResponse(**{c.name: getattr(team, c.name) for c in team.__table__.columns}, members=members)


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: str,
    body: TeamUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await require_role(db, team_id, current_user.id, "owner"):
        raise HTTPException(status_code=403, detail="Only the owner can update the team")
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(team, key, value)
    await db.commit()
    await db.refresh(team)
    return team


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await require_role(db, team_id, current_user.id, "owner"):
        raise HTTPException(status_code=403, detail="Only the owner can delete the team")
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    await db.delete(team)
    await db.commit()


@router.post("/{team_id}/invite", status_code=status.HTTP_201_CREATED)
async def invite_member(
    team_id: str,
    body: InviteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await require_role(db, team_id, current_user.id, "owner"):
        raise HTTPException(status_code=403, detail="Only the owner can invite members")
    if body.role not in ("editor", "viewer"):
        raise HTTPException(status_code=400, detail="Role must be editor or viewer")
    invitation = TeamInvitation(
        team_id=team_id, inviter_id=current_user.id,
        invitee_email=body.email, role=body.role,
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
    return {"id": invitation.id, "status": "pending"}


@router.put("/{team_id}/members/{user_id}")
async def update_member_role(
    team_id: str,
    user_id: str,
    body: UpdateMemberRoleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await require_role(db, team_id, current_user.id, "owner"):
        raise HTTPException(status_code=403, detail="Only the owner can change roles")
    if body.role not in ("editor", "viewer"):
        raise HTTPException(status_code=400, detail="Role must be editor or viewer")
    result = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    if member.role == "owner":
        raise HTTPException(status_code=400, detail="Cannot change owner role")
    member.role = body.role
    await db.commit()
    return {"status": "ok"}


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    team_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.id != user_id:
        if not await require_role(db, team_id, current_user.id, "owner"):
            raise HTTPException(status_code=403, detail="Only the owner can remove members")
    result = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    if member.role == "owner":
        raise HTTPException(status_code=400, detail="Cannot remove the owner")
    await db.delete(member)
    await db.commit()


@router.get("/{team_id}/mindmaps", response_model=list[MindMapListItem])
async def list_team_mindmaps(
    team_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    role = await get_member_role(db, team_id, current_user.id)
    if role is None:
        raise HTTPException(status_code=403, detail="Not a member")
    return await get_team_mindmaps(db, team_id)


@router.post("/{team_id}/mindmaps", response_model=MindMapResponse, status_code=status.HTTP_201_CREATED)
async def create_team_mindmap(
    team_id: str,
    body: MindMapCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await require_role(db, team_id, current_user.id, "editor"):
        raise HTTPException(status_code=403, detail="Viewers cannot create mind maps")
    mindmap = MindMap(
        owner_id=current_user.id, title=body.title,
        data=body.data, config=body.config, team_id=team_id,
    )
    db.add(mindmap)
    await db.commit()
    await db.refresh(mindmap)
    return mindmap
