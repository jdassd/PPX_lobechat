from datetime import datetime
from typing import Any

from pydantic import BaseModel


class MindMapCreate(BaseModel):
    title: str = "Untitled"
    data: dict[str, Any] = {}
    config: dict[str, Any] = {}
    team_id: str | None = None


class MindMapUpdate(BaseModel):
    title: str | None = None
    data: dict[str, Any] | None = None
    config: dict[str, Any] | None = None


class MindMapResponse(BaseModel):
    id: str
    owner_id: str
    title: str
    data: dict[str, Any]
    config: dict[str, Any]
    team_id: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MindMapListItem(BaseModel):
    id: str
    owner_id: str
    title: str
    team_id: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
