from datetime import datetime

from pydantic import BaseModel, EmailStr


class TeamCreate(BaseModel):
    name: str
    description: str | None = None


class TeamUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class TeamMemberResponse(BaseModel):
    id: str
    user_id: str
    email: str
    display_name: str
    role: str
    joined_at: datetime


class TeamResponse(BaseModel):
    id: str
    name: str
    description: str | None
    owner_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TeamDetailResponse(TeamResponse):
    members: list[TeamMemberResponse] = []


class InviteRequest(BaseModel):
    email: EmailStr
    role: str = "viewer"


class UpdateMemberRoleRequest(BaseModel):
    role: str


class InvitationResponse(BaseModel):
    id: str
    team_id: str
    team_name: str | None = None
    inviter_email: str | None = None
    invitee_email: str
    role: str
    status: str
    created_at: datetime
    expires_at: datetime
