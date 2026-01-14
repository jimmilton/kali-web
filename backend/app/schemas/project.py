"""Project and project membership schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field

from app.models.project import ProjectRole, ProjectStatus
from app.schemas.common import BaseSchema, PaginatedResponse, TimestampSchema


class ScopeDefinition(BaseSchema):
    """Schema for project scope definition."""

    domains: List[str] = []
    ips: List[str] = []
    urls: List[str] = []
    exclude: List[str] = []
    notes: Optional[str] = None


class ProjectBase(BaseSchema):
    """Base project schema."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    scope: Optional[ScopeDefinition] = None
    settings: Dict[str, Any] = {}


class ProjectCreate(ProjectBase):
    """Schema for creating a new project."""

    pass


class ProjectUpdate(BaseSchema):
    """Schema for updating a project."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    scope: Optional[ScopeDefinition] = None
    settings: Optional[Dict[str, Any]] = None


class ProjectMemberResponse(BaseSchema):
    """Schema for project member response."""

    user_id: UUID
    username: str
    email: str
    role: ProjectRole
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class ProjectStats(BaseSchema):
    """Schema for project statistics."""

    total_assets: int = 0
    total_jobs: int = 0
    total_vulnerabilities: int = 0
    vulnerabilities_by_severity: Dict[str, int] = {}
    recent_activity: int = 0


class ProjectResponse(ProjectBase, TimestampSchema):
    """Schema for project response."""

    id: UUID
    created_by: Optional[UUID] = None
    members: List[ProjectMemberResponse] = []
    stats: Optional[ProjectStats] = None


class ProjectListResponse(PaginatedResponse[ProjectResponse]):
    """Paginated project list response."""

    pass


class ProjectMemberCreate(BaseSchema):
    """Schema for adding a project member."""

    user_id: UUID
    role: ProjectRole = ProjectRole.MEMBER


class ProjectMemberUpdate(BaseSchema):
    """Schema for updating a project member."""

    role: ProjectRole


class ProjectExport(BaseSchema):
    """Schema for project export."""

    include_assets: bool = True
    include_vulnerabilities: bool = True
    include_credentials: bool = False
    include_reports: bool = True
    format: str = "json"
