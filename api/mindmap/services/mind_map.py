from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.mindmap.models.mind_map import MindMap
from api.mindmap.models.team import TeamMember


async def get_user_mindmaps(db: AsyncSession, user_id: str) -> list[MindMap]:
    result = await db.execute(
        select(MindMap).where(MindMap.owner_id == user_id, MindMap.team_id.is_(None)).order_by(MindMap.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_team_mindmaps(db: AsyncSession, team_id: str) -> list[MindMap]:
    result = await db.execute(
        select(MindMap).where(MindMap.team_id == team_id).order_by(MindMap.updated_at.desc())
    )
    return list(result.scalars().all())


async def can_access_mindmap(db: AsyncSession, user_id: str, mindmap: MindMap) -> str | None:
    """Returns the user's role for this mindmap, or None if no access."""
    if mindmap.owner_id == user_id:
        return "owner"
    if mindmap.team_id:
        result = await db.execute(
            select(TeamMember).where(TeamMember.team_id == mindmap.team_id, TeamMember.user_id == user_id)
        )
        member = result.scalar_one_or_none()
        if member:
            return member.role
    return None
