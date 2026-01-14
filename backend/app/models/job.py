"""Job and job-related models for tool execution."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, JSONB, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User
    from app.models.asset import Asset
    from app.models.result import Result
    from app.models.vulnerability import Vulnerability
    from app.models.credential import Credential


class JobStatus(str, Enum):
    """Job status enumeration."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class JobPriority(int, Enum):
    """Job priority levels."""

    LOW = 1
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


class Job(Base, UUIDMixin, TimestampMixin):
    """Job model for tracking tool executions."""

    __tablename__ = "jobs"

    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Job configuration
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    command: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Execution status
    status: Mapped[str] = mapped_column(
        String(50), default=JobStatus.PENDING.value, nullable=False, index=True
    )
    priority: Mapped[int] = mapped_column(Integer, default=JobPriority.NORMAL.value, nullable=False)

    # Container tracking
    container_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Execution results
    exit_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=3600, nullable=False)

    # Scheduling (for scheduled jobs)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cron_expression: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Creator
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Workflow reference (if part of a workflow)
    workflow_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("workflow_runs.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="jobs")
    creator: Mapped[Optional["User"]] = relationship("User", back_populates="jobs")
    targets: Mapped[List["JobTarget"]] = relationship(
        "JobTarget", back_populates="job", cascade="all, delete-orphan"
    )
    outputs: Mapped[List["JobOutput"]] = relationship(
        "JobOutput", back_populates="job", cascade="all, delete-orphan", order_by="JobOutput.sequence"
    )
    results: Mapped[List["Result"]] = relationship(
        "Result", back_populates="job", cascade="all, delete-orphan"
    )
    discovered_assets: Mapped[List["Asset"]] = relationship(
        "Asset", back_populates="discovery_job", foreign_keys="Asset.discovered_by"
    )
    discovered_vulnerabilities: Mapped[List["Vulnerability"]] = relationship(
        "Vulnerability", back_populates="discovery_job", foreign_keys="Vulnerability.discovered_by"
    )
    discovered_credentials: Mapped[List["Credential"]] = relationship(
        "Credential", back_populates="discovery_job", foreign_keys="Credential.discovered_by"
    )

    def __repr__(self) -> str:
        return f"<Job {self.tool_name} ({self.status})>"


class JobTarget(Base):
    """Job target model for tracking which assets a job targets."""

    __tablename__ = "job_targets"

    job_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("assets.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="targets")
    asset: Mapped["Asset"] = relationship("Asset")

    def __repr__(self) -> str:
        return f"<JobTarget job={self.job_id} asset={self.asset_id}>"


class JobOutput(Base, UUIDMixin):
    """Job output model for storing command output chunks."""

    __tablename__ = "job_outputs"

    job_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    output_type: Mapped[str] = mapped_column(String(20), default="stdout", nullable=False)  # stdout, stderr
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="outputs")

    def __repr__(self) -> str:
        return f"<JobOutput job={self.job_id} seq={self.sequence}>"
