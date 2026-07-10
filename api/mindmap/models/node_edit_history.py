import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from api.mindmap.database import Base


def _gen_uuid():
    return str(uuid.uuid4())


class NodeEditHistory(Base):
    __tablename__ = "node_edit_histories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_uuid)
    mindmap_id: Mapped[str] = mapped_column(String(36), ForeignKey("mind_maps.id", ondelete="CASCADE"), nullable=False, index=True)
    node_uid: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    edited_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
