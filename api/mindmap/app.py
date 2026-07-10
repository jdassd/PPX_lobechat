from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.mindmap.config import load_config
from api.mindmap.db import init_db, set_db_path
from api.mindmap.routers import auth, export, maps, nodes, teams
from api.mindmap.ws import handler as ws_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = load_config()
    os.makedirs(os.path.dirname(config.database) or ".", exist_ok=True)
    set_db_path(config.database)
    await init_db()
    yield


def create_app(static_dir: str | None = None) -> FastAPI:
    app = FastAPI(title="MindMap", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(maps.router)
    app.include_router(nodes.router)
    app.include_router(teams.router)
    app.include_router(export.router)
    app.include_router(ws_handler.router)

    # 挂载前端构建产物（由宿主传入；默认取仓库内 static/mindmap）
    if static_dir is None:
        static_dir = str(Path(__file__).resolve().parent.parent.parent / "static" / "mindmap")
    if os.path.isdir(static_dir):
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app
