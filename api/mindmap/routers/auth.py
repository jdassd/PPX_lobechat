from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from api.mindmap.auth import create_access_token, create_refresh_token, get_current_user
from api.mindmap.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    display_name: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


@router.post("/register", status_code=201)
async def register(req: RegisterRequest):
    if len(req.username) < 2:
        raise HTTPException(status_code=400, detail="Username must be at least 2 characters")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    result = await auth_service.register_user(
        username=req.username,
        email=req.email,
        password=req.password,
        display_name=req.display_name,
    )
    if "error" in result:
        raise HTTPException(status_code=409, detail=result["error"])

    # Auto-login after registration
    access_token = create_access_token(result["id"], result["username"])
    refresh_token, refresh_expires = create_refresh_token(result["id"])
    await auth_service.store_refresh_token(result["id"], refresh_token, refresh_expires)

    return {
        "user": result,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/login")
async def login(req: LoginRequest):
    user = await auth_service.authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = create_access_token(user["id"], user["username"])
    refresh_token, refresh_expires = create_refresh_token(user["id"])
    await auth_service.store_refresh_token(user["id"], refresh_token, refresh_expires)

    return {
        "user": user,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh")
async def refresh(req: RefreshRequest):
    token_info = await auth_service.validate_refresh_token(req.refresh_token)
    if not token_info:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Revoke old refresh token (rotation)
    await auth_service.revoke_refresh_token(req.refresh_token)

    # Issue new tokens
    access_token = create_access_token(token_info["user_id"], token_info["username"])
    new_refresh_token, refresh_expires = create_refresh_token(token_info["user_id"])
    await auth_service.store_refresh_token(token_info["user_id"], new_refresh_token, refresh_expires)

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user


@router.post("/logout")
async def logout(req: LogoutRequest, user: dict = Depends(get_current_user)):
    await auth_service.revoke_refresh_token(req.refresh_token)
    return {"message": "Logged out"}
