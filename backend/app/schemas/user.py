"""User and authentication schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.models.user import UserRole
from app.schemas.common import BaseSchema, TimestampSchema


class UserBase(BaseSchema):
    """Base user schema."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(..., min_length=8, max_length=100)
    role: UserRole = UserRole.OPERATOR

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseSchema):
    """Schema for updating a user."""

    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    avatar_url: Optional[str] = None


class UserResponse(UserBase, TimestampSchema):
    """Schema for user response."""

    id: UUID
    role: UserRole
    is_active: bool
    is_superuser: bool
    mfa_enabled: bool
    avatar_url: Optional[str] = None


class UserInDB(UserResponse):
    """Schema for user in database (includes hashed password)."""

    password_hash: str


class LoginRequest(BaseSchema):
    """Schema for login request."""

    username: str
    password: str
    mfa_code: Optional[str] = None


class RegisterRequest(UserCreate):
    """Schema for registration request."""

    confirm_password: str

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


class PasswordChange(BaseSchema):
    """Schema for password change request."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class Token(BaseSchema):
    """Schema for authentication token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseSchema):
    """Schema for JWT token payload."""

    sub: str  # user_id
    exp: datetime
    iat: datetime
    type: str  # access or refresh


class RefreshTokenRequest(BaseSchema):
    """Schema for refresh token request."""

    refresh_token: str


class MFASetup(BaseSchema):
    """Schema for MFA setup response."""

    secret: str
    qr_code: str  # base64 encoded QR code image
    backup_codes: list[str]


class MFAVerify(BaseSchema):
    """Schema for MFA verification request."""

    code: str = Field(..., min_length=6, max_length=6)


class PasswordResetRequest(BaseSchema):
    """Schema for requesting a password reset."""

    email: EmailStr


class PasswordResetConfirm(BaseSchema):
    """Schema for confirming a password reset."""

    token: str
    new_password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class PasswordResetResponse(BaseSchema):
    """Schema for password reset response."""

    message: str
    reset_token: Optional[str] = None  # Only returned in dev mode for testing
