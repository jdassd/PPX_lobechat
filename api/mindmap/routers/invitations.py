from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.mindmap.database import get_db
from api.mindmap.middleware.auth import get_current_user
from api.mindmap.models.invitation import TeamInvitation
from api.mindmap.models.team import Team, TeamMember
from api.mindmap.models.user import User
from api.mindmap.schemas.team import InvitationResponse

router = APIRouter(prefix="/api/invitations", tags=["invitations"])


@router.get("", response_model=list[InvitationResponse])
async def list_invitations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TeamInvitation, Team.name, User.email)
        .join(Team, TeamInvitation.team_id == Team.id)
        .join(User, TeamInvitation.inviter_id == User.id)
        .where(TeamInvitation.invitee_email == current_user.email, TeamInvitation.status == "pending")
        .order_by(TeamInvitation.created_at.desc())
    )
    invitations = []
    for inv, team_name, inviter_email in result.all():
        invitations.append(InvitationResponse(
            id=inv.id, team_id=inv.team_id, team_name=team_name,
            inviter_email=inviter_email, invitee_email=inv.invitee_email,
            role=inv.role, status=inv.status,
            created_at=inv.created_at, expires_at=inv.expires_at,
        ))
    return invitations


@router.post("/{invitation_id}/accept")
async def accept_invitation(
    invitation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(TeamInvitation).where(TeamInvitation.id == invitation_id))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if inv.invitee_email != current_user.email:
        raise HTTPException(status_code=403, detail="Not your invitation")
    if inv.status != "pending":
        raise HTTPException(status_code=400, detail="Invitation already processed")
    if inv.expires_at < datetime.utcnow():
        inv.status = "expired"
        await db.commit()
        raise HTTPException(status_code=400, detail="Invitation expired")
    existing = await db.execute(
        select(TeamMember).where(TeamMember.team_id == inv.team_id, TeamMember.user_id == current_user.id)
    )
    if existing.scalar_one_or_none():
        inv.status = "accepted"
        await db.commit()
        return {"status": "already_member"}
    member = TeamMember(team_id=inv.team_id, user_id=current_user.id, role=inv.role)
    db.add(member)
    inv.status = "accepted"
    await db.commit()
    return {"status": "accepted"}


@router.post("/{invitation_id}/decline")
async def decline_invitation(
    invitation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(TeamInvitation).where(TeamInvitation.id == invitation_id))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if inv.invitee_email != current_user.email:
        raise HTTPException(status_code=403, detail="Not your invitation")
    if inv.status != "pending":
        raise HTTPException(status_code=400, detail="Invitation already processed")
    inv.status = "declined"
    await db.commit()
    return {"status": "declined"}
