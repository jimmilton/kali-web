"""Workflow and workflow run schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field

from app.models.workflow import NodeType, WorkflowStatus
from app.schemas.common import BaseSchema, PaginatedResponse, TimestampSchema


class Position(BaseSchema):
    """Schema for node position."""

    x: float
    y: float


class WorkflowNodeData(BaseSchema):
    """Schema for workflow node data."""

    label: str
    tool: Optional[str] = None
    parameters: Dict[str, Any] = {}
    condition: Optional[str] = None
    condition_value: Optional[Any] = None
    delay_seconds: Optional[int] = None
    notification_type: Optional[str] = None
    notification_message: Optional[str] = None


class WorkflowNode(BaseSchema):
    """Schema for workflow node."""

    id: str
    type: NodeType
    position: Position
    data: WorkflowNodeData


class WorkflowEdge(BaseSchema):
    """Schema for workflow edge."""

    id: str
    source: str
    target: str
    source_handle: Optional[str] = None
    target_handle: Optional[str] = None
    label: Optional[str] = None
    condition: Optional[str] = None  # on_success, on_failure, on_complete, custom


class WorkflowDefinition(BaseSchema):
    """Schema for workflow definition."""

    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]


class WorkflowSettings(BaseSchema):
    """Schema for workflow settings."""

    max_parallel: int = 5
    retry_failed: bool = False
    retry_count: int = 3
    notify_on_complete: bool = False
    notify_on_failure: bool = True
    timeout_seconds: int = 86400


class WorkflowBase(BaseSchema):
    """Base workflow schema."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    definition: WorkflowDefinition
    is_template: bool = False
    is_public: bool = False
    category: Optional[str] = None
    tags: List[str] = []
    settings: WorkflowSettings = WorkflowSettings()


class WorkflowCreate(WorkflowBase):
    """Schema for creating a workflow."""

    project_id: Optional[UUID] = None  # None for templates


class WorkflowUpdate(BaseSchema):
    """Schema for updating a workflow."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    definition: Optional[WorkflowDefinition] = None
    is_template: Optional[bool] = None
    is_public: Optional[bool] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    settings: Optional[WorkflowSettings] = None


class WorkflowResponse(WorkflowBase, TimestampSchema):
    """Schema for workflow response."""

    id: UUID
    project_id: Optional[UUID] = None
    created_by: Optional[UUID] = None

    # Stats
    run_count: Optional[int] = None
    last_run_at: Optional[datetime] = None
    success_rate: Optional[float] = None


class WorkflowListResponse(PaginatedResponse[WorkflowResponse]):
    """Paginated workflow list response."""

    pass


class WorkflowRunCreate(BaseSchema):
    """Schema for creating a workflow run."""

    workflow_id: UUID
    project_id: UUID
    input_params: Dict[str, Any] = {}


class NodeExecutionLog(BaseSchema):
    """Schema for node execution log entry."""

    node_id: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    job_id: Optional[UUID] = None


class WorkflowRunResponse(TimestampSchema):
    """Schema for workflow run response."""

    id: UUID
    workflow_id: UUID
    project_id: UUID
    status: WorkflowStatus
    current_node_id: Optional[str] = None
    current_step: int
    context: Dict[str, Any]
    input_params: Dict[str, Any]
    execution_log: List[NodeExecutionLog]
    error_message: Optional[str] = None
    error_node_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: Optional[UUID] = None

    # Related data
    workflow_name: Optional[str] = None
    duration_seconds: Optional[int] = None


class WorkflowRunListResponse(PaginatedResponse[WorkflowRunResponse]):
    """Paginated workflow run list response."""

    pass


class WorkflowFilter(BaseSchema):
    """Schema for workflow filtering."""

    is_template: Optional[bool] = None
    is_public: Optional[bool] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    created_by: Optional[UUID] = None
    search: Optional[str] = None


class WorkflowRunFilter(BaseSchema):
    """Schema for workflow run filtering."""

    workflow_id: Optional[UUID] = None
    statuses: Optional[List[WorkflowStatus]] = None
    created_by: Optional[UUID] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class WorkflowTemplate(BaseSchema):
    """Schema for workflow template."""

    id: str
    name: str
    description: str
    category: str
    definition: WorkflowDefinition
    tags: List[str] = []
    preview_image: Optional[str] = None


class WorkflowApprovalRequest(BaseSchema):
    """Schema for approving a workflow manual step."""

    node_id: str = Field(..., description="The node ID that is being approved")
    option: str = Field(
        default="approve",
        description="The approval option (e.g., 'approve', 'reject')"
    )
    comment: Optional[str] = Field(
        None,
        description="Optional comment for the approval"
    )
