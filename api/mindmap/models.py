from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class Map:
    id: str
    name: str
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Node:
    id: str
    map_id: str
    parent_id: str | None = None
    content: str = ""
    position: int = 0
    style: str = "{}"
    collapsed: bool = False
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["collapsed"] = bool(d["collapsed"])
        return d
