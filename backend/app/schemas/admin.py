from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import PageResponse


class AdminUserResponse(BaseModel):
    id: UUID
    username: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminUserListResponse(BaseModel):
    items: list[AdminUserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=64)
    confirm_password: str = Field(..., min_length=8, max_length=64)


class ChangeRoleRequest(BaseModel):
    role: str = Field(..., pattern=r"^(admin|trader)$")
