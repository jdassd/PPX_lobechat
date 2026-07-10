from __future__ import annotations

import logging
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from api.mindmap.auth import get_current_user
from api.mindmap.services import export_service, map_service, permission_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/maps", tags=["export"])

EXPORT_FORMATS = {
    "docx": {
        "fn": export_service.export_docx,
        "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "ext": ".docx",
    },
    "xlsx": {
        "fn": export_service.export_xlsx,
        "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "ext": ".xlsx",
    },
    "xmind": {
        "fn": export_service.export_xmind,
        "content_type": "application/zip",
        "ext": ".xmind",
    },
}


@router.get("/{map_id}/export/{format}")
async def export_map(map_id: str, format: str, user: dict = Depends(get_current_user)):
    logger.info("Export request: map_id=%s, format=%s, user=%s", map_id, format, user.get("id"))

    if format not in EXPORT_FORMATS:
        logger.warning("Unsupported export format: %s", format)
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}. Use: {', '.join(EXPORT_FORMATS)}")

    try:
        has_access = await permission_service.check_map_access(user["id"], map_id, "view")
    except Exception:
        logger.exception("Permission check failed: map_id=%s, user=%s", map_id, user.get("id"))
        raise
    if not has_access:
        logger.warning("Access denied: map_id=%s, user=%s", map_id, user.get("id"))
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        map_data = await map_service.get_map_with_nodes(map_id)
    except Exception:
        logger.exception("Failed to fetch map data: map_id=%s", map_id)
        raise
    if not map_data:
        logger.warning("Map not found: map_id=%s", map_id)
        raise HTTPException(status_code=404, detail="Map not found")

    logger.info("Exporting map '%s' (%d nodes) as %s", map_data["name"], len(map_data["nodes"]), format)

    fmt = EXPORT_FORMATS[format]
    try:
        buf = fmt["fn"](map_data["name"], map_data["nodes"])
    except Exception:
        logger.exception("Export generation failed: map_id=%s, format=%s, map_name='%s', nodes_count=%d",
                         map_id, format, map_data["name"], len(map_data["nodes"]))
        raise HTTPException(status_code=500, detail=f"Failed to generate {format} file")

    # Use RFC 5987 encoding for non-ASCII filenames
    raw_filename = f"{map_data['name']}{fmt['ext']}"
    encoded_filename = quote(raw_filename)
    content_disposition = f"attachment; filename*=UTF-8''{encoded_filename}"

    logger.info("Export successful: map_id=%s, format=%s, filename='%s'", map_id, format, raw_filename)

    return StreamingResponse(
        buf,
        media_type=fmt["content_type"],
        headers={"Content-Disposition": content_disposition},
    )
