"""Job and job output schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field

from app.models.job import JobPriority, JobStatus
from app.schemas.common import BaseSchema, PaginatedResponse, TimestampSchema


class JobBase(BaseSchema):
    """Base job schema."""

    tool_name: str = Field(..., min_length=1, max_length=100)
    parameters: Dict[str, Any] = {}
    priority: int = JobPriority.NORMAL.value
    timeout_seconds: int = 3600


class JobCreate(JobBase):
    """Schema for creating a new job."""

    project_id: UUID
    target_asset_ids: List[UUID] = []
    scheduled_at: Optional[datetime] = None


class JobUpdate(BaseSchema):
    """Schema for updating a job."""

    parameters: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None
    timeout_seconds: Optional[int] = None
    scheduled_at: Optional[datetime] = None


class JobTargetResponse(BaseSchema):
    """Schema for job target response."""

    asset_id: UUID
    asset_type: str
    asset_value: str


class JobOutputResponse(BaseSchema):
    """Schema for job output response."""

    id: UUID
    sequence: int
    output_type: str
    content: str
    timestamp: datetime


class JobResponse(JobBase, TimestampSchema):
    """Schema for job response."""

    id: UUID
    project_id: UUID
    command: Optional[str] = None
    status: JobStatus
    container_id: Optional[str] = None
    celery_task_id: Optional[str] = None
    exit_code: Optional[int] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None
    created_by: Optional[UUID] = None
    workflow_run_id: Optional[UUID] = None

    # Related data
    targets: List[JobTargetResponse] = []
    result_count: Optional[int] = None
    discovered_assets: Optional[int] = None
    discovered_vulnerabilities: Optional[int] = None


class JobListResponse(PaginatedResponse[JobResponse]):
    """Paginated job list response."""

    pass


class JobOutputListResponse(BaseSchema):
    """Schema for job output list response."""

    job_id: UUID
    outputs: List[JobOutputResponse]
    total: int
    has_more: bool


class JobFilter(BaseSchema):
    """Schema for job filtering."""

    tool_names: Optional[List[str]] = None
    statuses: Optional[List[JobStatus]] = None
    created_by: Optional[UUID] = None
    project_id: Optional[UUID] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class JobAction(BaseSchema):
    """Schema for job action (cancel, retry, etc.)."""

    action: str  # cancel, retry, pause, resume
    reason: Optional[str] = None


class JobBulkAction(BaseSchema):
    """Schema for bulk job action."""

    job_ids: List[UUID]
    action: str
    reason: Optional[str] = None
