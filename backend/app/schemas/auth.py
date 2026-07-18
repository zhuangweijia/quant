from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.passwords import validate_bcrypt_password_size


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=64)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str):
        return validate_bcrypt_password_size(value)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=8, max_length=64)
    confirm_password: str = Field(..., min_length=8, max_length=64)

    @field_validator("password", "confirm_password")
    @classmethod
    def password_fits_bcrypt(cls, value: str):
        return validate_bcrypt_password_size(value)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: UUID
    username: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=8, max_length=64)
    new_password: str = Field(..., min_length=8, max_length=64)
    confirm_password: str = Field(..., min_length=8, max_length=64)

    @field_validator("old_password", "new_password", "confirm_password")
    @classmethod
    def password_fits_bcrypt(cls, value: str):
        return validate_bcrypt_password_size(value)
