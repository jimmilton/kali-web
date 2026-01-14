"""Audit log model for tracking user actions."""

import uuid
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, JSONB, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class AuditAction(str, Enum):
    """Audit action enumeration."""

    # Auth
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"
    MFA_ENABLE = "mfa_enable"
    MFA_DISABLE = "mfa_disable"

    # User management
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"

    # Project
    PROJECT_CREATE = "project_create"
    PROJECT_UPDATE = "project_update"
    PROJECT_DELETE = "project_delete"
    PROJECT_MEMBER_ADD = "project_member_add"
    PROJECT_MEMBER_REMOVE = "project_member_remove"

    # Asset
    ASSET_CREATE = "asset_create"
    ASSET_UPDATE = "asset_update"
    ASSET_DELETE = "asset_delete"
    ASSET_IMPORT = "asset_import"

    # Job
    JOB_CREATE = "job_create"
    JOB_START = "job_start"
    JOB_CANCEL = "job_cancel"
    JOB_COMPLETE = "job_complete"
    JOB_FAIL = "job_fail"

    # Vulnerability
    VULN_CREATE = "vuln_create"
    VULN_UPDATE = "vuln_update"
    VULN_DELETE = "vuln_delete"
    VULN_STATUS_CHANGE = "vuln_status_change"

    # Credential
    CREDENTIAL_CREATE = "credential_create"
    CREDENTIAL_VIEW = "credential_view"
    CREDENTIAL_DELETE = "credential_delete"

    # Workflow
    WORKFLOW_CREATE = "workflow_create"
    WORKFLOW_UPDATE = "workflow_update"
    WORKFLOW_DELETE = "workflow_delete"
    WORKFLOW_RUN = "workflow_run"

    # Report
    REPORT_CREATE = "report_create"
    REPORT_GENERATE = "report_generate"
    REPORT_DOWNLOAD = "report_download"
    REPORT_DELETE = "report_delete"

    # Integration
    INTEGRATION_CONFIGURE = "integration_configure"
    INTEGRATION_SYNC = "integration_sync"

    # System
    SETTINGS_UPDATE = "settings_update"
    BACKUP_CREATE = "backup_create"
    BACKUP_RESTORE = "backup_restore"


class AuditLog(Base, UUIDMixin, TimestampMixin):
    """Audit log model for tracking all user actions."""

    __tablename__ = "audit_logs"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Action details
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), nullable=True)

    # Additional details
    details: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    # {
    #     "before": {...},  # State before change
    #     "after": {...},   # State after change
    #     "changes": [...], # List of changed fields
    #     "reason": "...",  # Optional reason
    # }

    # Request context
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Status
    success: Mapped[bool] = mapped_column(default=True, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} by {self.user_id}>"
