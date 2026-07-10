from __future__ import annotations

from api.mindmap.db import get_db

# Role hierarchy: owner > admin > editor > viewer
ROLE_LEVELS = {
    "owner": 4,
    "admin": 3,
    "editor": 2,
    "viewer": 1,
}

# Permission requirements
PERMISSION_LEVELS = {
    "view": 1,    # viewer and above
    "edit": 2,    # editor and above
    "admin": 3,   # admin and above
    "owner": 4,   # owner only
}


def has_permission(role: str, permission: str) -> bool:
    return ROLE_LEVELS.get(role, 0) >= PERMISSION_LEVELS.get(permission, 999)


async def get_user_team_role(user_id: str, team_id: str) -> str | None:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT role FROM team_members WHERE team_id = ? AND user_id = ?",
            (team_id, user_id),
        )
        row = await cursor.fetchone()
        return row["role"] if row else None
    finally:
        await db.close()


async def check_map_access(user_id: str, map_id: str, permission: str = "view") -> bool:
    """Check if user has the required permission on a map.

    Rules:
    - Maps with owner_id=NULL (legacy) are accessible to all authenticated users
    - Personal maps (owner_id set, team_id=NULL) are only accessible to the owner
    - Team maps: check user's team role against required permission
    """
    db = await get_db()
    try:
        cursor = await db.execute("SELECT owner_id, team_id FROM maps WHERE id = ?", (map_id,))
        row = await cursor.fetchone()
        if not row:
            return False

        owner_id = row["owner_id"]
        team_id = row["team_id"]

        # Legacy maps (no owner) - accessible to all authenticated users
        if owner_id is None:
            return True

        # Personal map - owner has full access
        if owner_id == user_id and team_id is None:
            return True

        # Team map
        if team_id:
            role = await get_user_team_role(user_id, team_id)
            if role is None:
                return False
            return has_permission(role, permission)

        # Personal map, not the owner
        return False
    finally:
        await db.close()


async def check_team_access(user_id: str, team_id: str, permission: str = "view") -> bool:
    role = await get_user_team_role(user_id, team_id)
    if role is None:
        return False
    return has_permission(role, permission)
