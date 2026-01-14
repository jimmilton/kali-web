"""Pydantic schemas for API validation and serialization."""

from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserInDB,
    Token,
    TokenPayload,
    LoginRequest,
    RegisterRequest,
    PasswordChange,
    RefreshTokenRequest,
)
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    ProjectMemberCreate,
    ProjectMemberResponse,
    ScopeDefinition,
)
from app.schemas.asset import (
    AssetCreate,
    AssetUpdate,
    AssetResponse,
    AssetListResponse,
    AssetImport,
    AssetRelationCreate,
    AssetRelationResponse,
)
from app.schemas.job import (
    JobCreate,
    JobUpdate,
    JobResponse,
    JobListResponse,
    JobOutputResponse,
)
from app.schemas.tool import (
    ToolDefinition,
    ToolParameter,
    ToolCategory,
    ToolListResponse,
)
from app.schemas.vulnerability import (
    VulnerabilityCreate,
    VulnerabilityUpdate,
    VulnerabilityResponse,
    VulnerabilityListResponse,
)
from app.schemas.credential import (
    CredentialCreate,
    CredentialUpdate,
    CredentialResponse,
    CredentialListResponse,
)
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowRunCreate,
    WorkflowRunResponse,
    WorkflowNode,
    WorkflowEdge,
)
from app.schemas.report import (
    ReportCreate,
    ReportUpdate,
    ReportResponse,
    ReportListResponse,
)
from app.schemas.common import (
    PaginatedResponse,
    MessageResponse,
    ErrorResponse,
    HealthResponse,
)

__all__ = [
    # User
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserInDB",
    "Token",
    "TokenPayload",
    "LoginRequest",
    "RegisterRequest",
    "PasswordChange",
    "RefreshTokenRequest",
    # Project
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    "ProjectListResponse",
    "ProjectMemberCreate",
    "ProjectMemberResponse",
    "ScopeDefinition",
    # Asset
    "AssetCreate",
    "AssetUpdate",
    "AssetResponse",
    "AssetListResponse",
    "AssetImport",
    "AssetRelationCreate",
    "AssetRelationResponse",
    # Job
    "JobCreate",
    "JobUpdate",
    "JobResponse",
    "JobListResponse",
    "JobOutputResponse",
    # Tool
    "ToolDefinition",
    "ToolParameter",
    "ToolCategory",
    "ToolListResponse",
    # Vulnerability
    "VulnerabilityCreate",
    "VulnerabilityUpdate",
    "VulnerabilityResponse",
    "VulnerabilityListResponse",
    # Credential
    "CredentialCreate",
    "CredentialUpdate",
    "CredentialResponse",
    "CredentialListResponse",
    # Workflow
    "WorkflowCreate",
    "WorkflowUpdate",
    "WorkflowResponse",
    "WorkflowRunCreate",
    "WorkflowRunResponse",
    "WorkflowNode",
    "WorkflowEdge",
    # Report
    "ReportCreate",
    "ReportUpdate",
    "ReportResponse",
    "ReportListResponse",
    # Common
    "PaginatedResponse",
    "MessageResponse",
    "ErrorResponse",
    "HealthResponse",
]
