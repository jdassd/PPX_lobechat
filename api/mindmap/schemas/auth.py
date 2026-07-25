from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=64)


class LoginRequest(BaseModel):
    email: EmailStr
    # 登录保留较低下限以兼容升级前已经创建的短密码账户。
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=4096)


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    avatar_url: str | None
    created_at: datetime

    class Config:
        from_attributes = True
