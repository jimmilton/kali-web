"""Credential schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field

from app.models.credential import CredentialType, HashType
from app.schemas.common import BaseSchema, PaginatedResponse, TimestampSchema


class CredentialBase(BaseSchema):
    """Base credential schema."""

    credential_type: CredentialType = CredentialType.PASSWORD
    username: Optional[str] = Field(None, max_length=255)
    domain: Optional[str] = Field(None, max_length=255)
    service: Optional[str] = Field(None, max_length=100)
    port: Optional[int] = Field(None, ge=1, le=65535)
    url: Optional[str] = Field(None, max_length=500)
    hash_type: Optional[HashType] = None
    source: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class CredentialCreate(CredentialBase):
    """Schema for creating a credential."""

    project_id: UUID
    asset_id: Optional[UUID] = None

    # Sensitive fields
    password: Optional[str] = None
    hash_value: Optional[str] = None


class CredentialUpdate(BaseSchema):
    """Schema for updating a credential."""

    username: Optional[str] = Field(None, max_length=255)
    domain: Optional[str] = Field(None, max_length=255)
    service: Optional[str] = Field(None, max_length=100)
    port: Optional[int] = Field(None, ge=1, le=65535)
    url: Optional[str] = Field(None, max_length=500)
    is_valid: Optional[bool] = None
    notes: Optional[str] = None
    asset_id: Optional[UUID] = None


class CredentialAssetInfo(BaseSchema):
    """Schema for credential asset info."""

    id: UUID
    type: str
    value: str


class CredentialResponse(CredentialBase, TimestampSchema):
    """Schema for credential response (without sensitive data)."""

    id: UUID
    project_id: UUID
    asset_id: Optional[UUID] = None
    is_valid: Optional[bool] = None
    validated_at: Optional[str] = None
    discovered_by: Optional[UUID] = None
    fingerprint: Optional[str] = None
    metadata_: Dict[str, Any] = Field(default={}, alias="metadata")

    # Masked sensitive data
    has_password: bool = False
    has_hash: bool = False

    # Related data
    asset: Optional[CredentialAssetInfo] = None


class CredentialWithSecret(CredentialResponse):
    """Schema for credential response with sensitive data (restricted access)."""

    password: Optional[str] = None
    hash_value: Optional[str] = None


class CredentialListResponse(PaginatedResponse[CredentialResponse]):
    """Paginated credential list response."""

    pass


class CredentialFilter(BaseSchema):
    """Schema for credential filtering."""

    credential_types: Optional[List[CredentialType]] = None
    hash_types: Optional[List[HashType]] = None
    services: Optional[List[str]] = None
    is_valid: Optional[bool] = None
    has_password: Optional[bool] = None
    has_hash: Optional[bool] = None
    asset_ids: Optional[List[UUID]] = None
    search: Optional[str] = None


class CredentialStats(BaseSchema):
    """Schema for credential statistics."""

    total: int
    by_type: Dict[str, int]
    by_service: Dict[str, int]
    valid_count: int
    invalid_count: int
    unknown_count: int
    with_plaintext: int
    with_hash: int


class HashIdentifyRequest(BaseSchema):
    """Schema for hash identification request."""

    hash_value: str


class HashIdentifyResponse(BaseSchema):
    """Schema for hash identification response."""

    hash_value: str
    possible_types: List[Dict[str, Any]]
    # [{"type": "md5", "confidence": 0.95, "example": "..."}]


class CredentialValidateRequest(BaseSchema):
    """Schema for credential validation request."""

    credential_id: UUID
    target: Optional[str] = None  # Override target


class CredentialValidateResponse(BaseSchema):
    """Schema for credential validation response."""

    credential_id: UUID
    is_valid: bool
    message: Optional[str] = None
    validated_at: datetime
