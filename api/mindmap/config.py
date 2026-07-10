from __future__ import annotations

from pydantic import BaseModel


class AppConfig(BaseModel):
    port: int = 8323
    database: str = "./data/mindmap.db"
    jwt_secret: str = "CHANGE-ME-IN-PRODUCTION"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30


_config = AppConfig()


def configure(**kwargs) -> AppConfig:
    """由宿主（工具箱）在启动服务前注入运行配置。"""
    global _config
    _config = AppConfig(**{**_config.model_dump(), **kwargs})
    return _config


def load_config(path: str = "") -> AppConfig:
    """兼容原独立部署的调用签名；配置由 configure() 注入，path 参数被忽略。"""
    return _config
