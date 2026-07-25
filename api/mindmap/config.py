import os
import secrets

from pydantic_settings import BaseSettings

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")


class Settings(BaseSettings):
    DATABASE_URL: str = f"sqlite+aiosqlite:///{DATA_DIR}/mindmap.db"
    # 桌面入口会注入持久化密钥；独立启动未配置时也不再使用公开的固定弱密钥。
    JWT_SECRET: str = os.environ.get("JWT_SECRET") or secrets.token_urlsafe(48)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DATA_DIR: str = DATA_DIR

    class Config:
        env_file = ".env"


settings = Settings()
