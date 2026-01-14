"""Project and project membership models."""

import uuid
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, JSONB, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.asset import Asset
    from app.models.job import Job
    from app.models.vulnerability import Vulnerability
    from app.models.credential import Credential
    from app.models.workflow import Workflow, WorkflowRun
    from app.models.report import Report
    from app.models.note import Note


class ProjectStatus(str, Enum):
    """Project status enumeration."""

    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    ON_HOLD = "on_hold"


class ProjectRole(str, Enum):
    """Project member role enumeration."""

    OWNER = "owner"
    MANAGER = "manager"
    MEMBER = "member"
    VIEWER = "viewer"


class Project(Base, UUIDMixin, TimestampMixin):
    """Project model for organizing security assessments."""

    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default=ProjectStatus.ACTIVE.value, nullable=False
    )

    # Scope definition
    scope: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    # Example: {"domains": ["example.com"], "ips": ["192.168.1.0/24"], "exclude": ["*.admin.example.com"]}

    # Project settings
    settings: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Creator reference
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    creator: Mapped[Optional["User"]] = relationship(
        "User", back_populates="created_projects", foreign_keys=[created_by]
    )
    members: Mapped[List["ProjectMember"]] = relationship(
        "ProjectMember", back_populates="project", cascade="all, delete-orphan"
    )
    assets: Mapped[List["Asset"]] = relationship(
        "Asset", back_populates="project", cascade="all, delete-orphan"
    )
    jobs: Mapped[List["Job"]] = relationship(
        "Job", back_populates="project", cascade="all, delete-orphan"
    )
    vulnerabilities: Mapped[List["Vulnerability"]] = relationship(
        "Vulnerability", back_populates="project", cascade="all, delete-orphan"
    )
    credentials: Mapped[List["Credential"]] = relationship(
        "Credential", back_populates="project", cascade="all, delete-orphan"
    )
    workflows: Mapped[List["Workflow"]] = relationship(
        "Workflow", back_populates="project", cascade="all, delete-orphan"
    )
    workflow_runs: Mapped[List["WorkflowRun"]] = relationship(
        "WorkflowRun", back_populates="project", cascade="all, delete-orphan"
    )
    reports: Mapped[List["Report"]] = relationship(
        "Report", back_populates="project", cascade="all, delete-orphan"
    )
    notes: Mapped[List["Note"]] = relationship(
        "Note", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project {self.name}>"


class ProjectMember(Base):
    """Project membership model for user-project relationships."""

    __tablename__ = "project_members"

    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(
        String(50), default=ProjectRole.MEMBER.value, nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="project_memberships")

    def __repr__(self) -> str:
        return f"<ProjectMember project={self.project_id} user={self.user_id}>"
