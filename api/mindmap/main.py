import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.mindmap.database import create_tables
from api.mindmap.redis import close_redis
from api.mindmap.routers import auth, invitations, mindmaps, node_locks, teams

# Pydantic 验证错误 → 用户友好提示的映射
VALIDATION_FIELD_NAMES = {
    "email": "邮箱",
    "password": "密码",
    "display_name": "显示名称",
    "title": "标题",
    "role": "角色",
    "refresh_token": "刷新令牌",
}

VALIDATION_TYPE_MESSAGES = {
    "value_error": "格式不正确",
    "missing": "不能为空",
    "string_too_short": "长度不足",
    "string_too_long": "长度超出限制",
    "type_error": "类型不正确",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield
    await close_redis()


app = FastAPI(title="Mind Map API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    messages = []
    for error in exc.errors():
        field = error.get("loc", [])[-1] if error.get("loc") else "unknown"
        field_label = VALIDATION_FIELD_NAMES.get(field, field)
        error_type = error.get("type", "")
        # 匹配错误类型的前缀，如 "value_error.email" → "value_error"
        base_type = error_type.split(".")[0] if error_type else ""
        friendly_msg = VALIDATION_TYPE_MESSAGES.get(error_type) or VALIDATION_TYPE_MESSAGES.get(base_type)
        if friendly_msg:
            messages.append(f"{field_label}{friendly_msg}")
        else:
            messages.append(f"{field_label}输入有误")
    detail = "；".join(messages) if messages else "输入数据有误，请检查后重试"
    return JSONResponse(status_code=422, content={"detail": detail})


app.include_router(auth.router)
app.include_router(mindmaps.router)
app.include_router(teams.router)
app.include_router(invitations.router)
app.include_router(node_locks.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# 桌面内嵌：由本服务直接托管前端静态资源（原独立部署时由 nginx 承担）
_static_dir = os.environ.get("MINDMAP_STATIC_DIR", "")
if _static_dir and os.path.isdir(_static_dir):
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
