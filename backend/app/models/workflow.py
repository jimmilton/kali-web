"""Workflow and workflow run models for automation."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, JSONB, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class WorkflowStatus(str, Enum):
    """Workflow run status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeType(str, Enum):
    """Workflow node type enumeration."""

    TOOL = "tool"
    CONDITION = "condition"
    DELAY = "delay"
    NOTIFICATION = "notification"
    PARALLEL = "parallel"
    LOOP = "loop"
    MANUAL = "manual"


class Workflow(Base, UUIDMixin, TimestampMixin):
    """Workflow model for defining automation pipelines."""

    __tablename__ = "workflows"

    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Workflow definition (React Flow format)
    definition: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # Structure:
    # {
    #     "nodes": [
    #         {"id": "1", "type": "tool", "data": {"tool": "nmap", "params": {...}}, "position": {...}},
    #         {"id": "2", "type": "condition", "data": {"condition": "port_open", "value": 80}, "position": {...}},
    #     ],
    #     "edges": [
    #         {"id": "e1-2", "source": "1", "target": "2", "label": "on_complete"},
    #     ]
    # }

    # Template settings
    is_template: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tags: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=list, nullable=False)

    # Settings
    settings: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    # {
    #     "max_parallel": 5,
    #     "retry_failed": true,
    #     "notify_on_complete": true,
    # }

    # Creator
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="workflows")
    creator: Mapped[Optional["User"]] = relationship("User")
    runs: Mapped[List["WorkflowRun"]] = relationship(
        "WorkflowRun", back_populates="workflow", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Workflow {self.name}>"


class WorkflowRun(Base, UUIDMixin, TimestampMixin):
    """Workflow run model for tracking workflow executions."""

    __tablename__ = "workflow_runs"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Run status
    status: Mapped[str] = mapped_column(
        String(50), default=WorkflowStatus.PENDING.value, nullable=False, index=True
    )
    current_node_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    current_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Execution context (variables passed between nodes)
    context: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Input parameters (overrides for this run)
    input_params: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Execution log
    execution_log: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    # [
    #     {"node_id": "1", "status": "completed", "started_at": "...", "completed_at": "...", "result": {...}},
    #     {"node_id": "2", "status": "running", "started_at": "..."},
    # ]

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_node_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Creator
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="runs")
    project: Mapped["Project"] = relationship("Project", back_populates="workflow_runs")
    creator: Mapped[Optional["User"]] = relationship("User")

    def __repr__(self) -> str:
        return f"<WorkflowRun {self.id} ({self.status})>"
