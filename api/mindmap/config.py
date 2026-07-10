import os

from pydantic_settings import BaseSettings

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")


class Settings(BaseSettings):
    DATABASE_URL: str = f"sqlite+aiosqlite:///{DATA_DIR}/mindmap.db"
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DATA_DIR: str = DATA_DIR

    class Config:
        env_file = ".env"


settings = Settings()
