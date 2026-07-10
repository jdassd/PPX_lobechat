from datetime import datetime

from pydantic import BaseModel


class NodeEditHistoryCreate(BaseModel):
    node_uid: str
    user_display_name: str


class NodeEditHistoryResponse(BaseModel):
    id: str
    mindmap_id: str
    node_uid: str
    user_id: str
    user_display_name: str
    edited_at: datetime

    class Config:
        from_attributes = True
