from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.mindmap.database import get_db
from api.mindmap.middleware.auth import get_current_user
from api.mindmap.models.mind_map import MindMap
from api.mindmap.models.node_edit_history import NodeEditHistory
from api.mindmap.models.user import User
from api.mindmap.schemas.mind_map import MindMapCreate, MindMapListItem, MindMapResponse, MindMapUpdate
from api.mindmap.schemas.node_edit_history import NodeEditHistoryCreate, NodeEditHistoryResponse
from api.mindmap.services.mind_map import can_access_mindmap, get_user_mindmaps

router = APIRouter(prefix="/api/mindmaps", tags=["mindmaps"])


@router.get("", response_model=list[MindMapListItem])
async def list_mindmaps(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_user_mindmaps(db, current_user.id)


@router.post("", response_model=MindMapResponse, status_code=status.HTTP_201_CREATED)
async def create_mindmap(
    body: MindMapCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    mindmap = MindMap(
        owner_id=current_user.id,
        title=body.title,
        data=body.data,
        config=body.config,
        team_id=body.team_id,
    )
    db.add(mindmap)
    await db.commit()
    await db.refresh(mindmap)
    return mindmap


@router.get("/{mindmap_id}", response_model=MindMapResponse)
async def get_mindmap(
    mindmap_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MindMap).where(MindMap.id == mindmap_id))
    mindmap = result.scalar_one_or_none()
    if not mindmap:
        raise HTTPException(status_code=404, detail="Mind map not found")
    role = await can_access_mindmap(db, current_user.id, mindmap)
    if role is None:
        raise HTTPException(status_code=403, detail="Access denied")
    return mindmap


@router.put("/{mindmap_id}", response_model=MindMapResponse)
async def update_mindmap(
    mindmap_id: str,
    body: MindMapUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MindMap).where(MindMap.id == mindmap_id))
    mindmap = result.scalar_one_or_none()
    if not mindmap:
        raise HTTPException(status_code=404, detail="Mind map not found")
    role = await can_access_mindmap(db, current_user.id, mindmap)
    if role is None:
        raise HTTPException(status_code=403, detail="Access denied")
    if role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot edit")
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(mindmap, key, value)
    await db.commit()
    await db.refresh(mindmap)
    return mindmap


@router.delete("/{mindmap_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mindmap(
    mindmap_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MindMap).where(MindMap.id == mindmap_id))
    mindmap = result.scalar_one_or_none()
    if not mindmap:
        raise HTTPException(status_code=404, detail="Mind map not found")
    if mindmap.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can delete")
    await db.delete(mindmap)
    await db.commit()


@router.get("/{mindmap_id}/node-history", response_model=list[NodeEditHistoryResponse])
async def get_node_history(
    mindmap_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MindMap).where(MindMap.id == mindmap_id))
    mindmap = result.scalar_one_or_none()
    if not mindmap:
        raise HTTPException(status_code=404, detail="Mind map not found")
    role = await can_access_mindmap(db, current_user.id, mindmap)
    if role is None:
        raise HTTPException(status_code=403, detail="Access denied")
    result = await db.execute(
        select(NodeEditHistory)
        .where(NodeEditHistory.mindmap_id == mindmap_id)
        .order_by(NodeEditHistory.edited_at.desc())
    )
    return list(result.scalars().all())


@router.post("/{mindmap_id}/node-history", response_model=NodeEditHistoryResponse, status_code=status.HTTP_201_CREATED)
async def create_node_history(
    mindmap_id: str,
    body: NodeEditHistoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MindMap).where(MindMap.id == mindmap_id))
    mindmap = result.scalar_one_or_none()
    if not mindmap:
        raise HTTPException(status_code=404, detail="Mind map not found")
    role = await can_access_mindmap(db, current_user.id, mindmap)
    if role is None:
        raise HTTPException(status_code=403, detail="Access denied")
    if role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot edit")
    # Upsert: update existing record for same mindmap+node, or create new one
    existing_result = await db.execute(
        select(NodeEditHistory).where(
            NodeEditHistory.mindmap_id == mindmap_id,
            NodeEditHistory.node_uid == body.node_uid
        )
    )
    record = existing_result.scalar_one_or_none()
    if record:
        record.user_id = current_user.id
        record.user_display_name = body.user_display_name
        record.edited_at = datetime.now(timezone.utc)
    else:
        record = NodeEditHistory(
            mindmap_id=mindmap_id,
            node_uid=body.node_uid,
            user_id=current_user.id,
            user_display_name=body.user_display_name,
            edited_at=datetime.now(timezone.utc),
        )
        db.add(record)
    await db.commit()
    await db.refresh(record)
    return record
