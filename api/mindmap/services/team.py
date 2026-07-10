from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.mindmap.models.team import Team, TeamMember


async def get_user_teams(db: AsyncSession, user_id: str) -> list[dict]:
    result = await db.execute(
        select(Team, TeamMember.role)
        .join(TeamMember, Team.id == TeamMember.team_id)
        .where(TeamMember.user_id == user_id)
        .order_by(Team.updated_at.desc())
    )
    return [{"team": row[0], "role": row[1]} for row in result.all()]


async def get_member_role(db: AsyncSession, team_id: str, user_id: str) -> str | None:
    result = await db.execute(
        select(TeamMember.role).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def require_role(db: AsyncSession, team_id: str, user_id: str, min_role: str) -> str | None:
    """Check if user has at least the minimum role. Returns role or None."""
    role = await get_member_role(db, team_id, user_id)
    if role is None:
        return None
    hierarchy = {"viewer": 0, "editor": 1, "owner": 2}
    if hierarchy.get(role, -1) >= hierarchy.get(min_role, 99):
        return role
    return None
