"""Asset and asset relationship schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field

from app.models.asset import AssetStatus, AssetType, RelationType
from app.schemas.common import BaseSchema, PaginatedResponse, TimestampSchema


class AssetBase(BaseSchema):
    """Base asset schema."""

    type: AssetType
    value: str = Field(..., min_length=1, max_length=500)
    metadata_: Dict[str, Any] = Field(default={}, alias="metadata")
    tags: List[str] = []
    status: AssetStatus = AssetStatus.ACTIVE


class AssetCreate(AssetBase):
    """Schema for creating a new asset."""

    project_id: UUID


class AssetUpdate(BaseSchema):
    """Schema for updating an asset."""

    value: Optional[str] = Field(None, min_length=1, max_length=500)
    metadata_: Optional[Dict[str, Any]] = Field(None, alias="metadata")
    tags: Optional[List[str]] = None
    status: Optional[AssetStatus] = None
    risk_score: Optional[int] = Field(None, ge=0, le=100)


class AssetRelationResponse(BaseSchema):
    """Schema for asset relation response."""

    parent_id: UUID
    child_id: UUID
    relation_type: RelationType
    parent_value: Optional[str] = None
    child_value: Optional[str] = None


class AssetResponse(AssetBase, TimestampSchema):
    """Schema for asset response."""

    id: UUID
    project_id: UUID
    risk_score: int
    discovered_by: Optional[UUID] = None

    # Related data
    vulnerability_count: Optional[int] = None
    credential_count: Optional[int] = None
    child_relations: List[AssetRelationResponse] = []
    parent_relations: List[AssetRelationResponse] = []


class AssetListResponse(PaginatedResponse[AssetResponse]):
    """Paginated asset list response."""

    pass


class AssetImportItem(BaseSchema):
    """Schema for a single asset import item."""

    type: AssetType
    value: str
    metadata_: Dict[str, Any] = Field(default={}, alias="metadata")
    tags: List[str] = []


class AssetImport(BaseSchema):
    """Schema for bulk asset import."""

    assets: List[AssetImportItem]
    skip_duplicates: bool = True
    auto_detect_type: bool = False


class AssetImportResult(BaseSchema):
    """Schema for asset import result."""

    imported: int
    skipped: int
    errors: List[Dict[str, Any]] = []


class AssetRelationCreate(BaseSchema):
    """Schema for creating an asset relation."""

    parent_id: UUID
    child_id: UUID
    relation_type: RelationType
    metadata_: Dict[str, Any] = Field(default={}, alias="metadata")


class AssetFilter(BaseSchema):
    """Schema for asset filtering."""

    types: Optional[List[AssetType]] = None
    tags: Optional[List[str]] = None
    status: Optional[AssetStatus] = None
    min_risk_score: Optional[int] = None
    max_risk_score: Optional[int] = None
    has_vulnerabilities: Optional[bool] = None
    search: Optional[str] = None


class AssetGraph(BaseSchema):
    """Schema for asset relationship graph."""

    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
