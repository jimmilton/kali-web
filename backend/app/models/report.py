"""Report model for generating security reports."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, JSONB, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class ReportTemplate(str, Enum):
    """Report template enumeration."""

    EXECUTIVE = "executive"
    TECHNICAL = "technical"
    COMPLIANCE = "compliance"
    VULNERABILITY = "vulnerability"
    ASSET = "asset"
    CUSTOM = "custom"


class ReportFormat(str, Enum):
    """Report format enumeration."""

    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    MARKDOWN = "md"
    JSON = "json"


class ReportStatus(str, Enum):
    """Report generation status."""

    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class Report(Base, UUIDMixin, TimestampMixin):
    """Report model for security assessment reports."""

    __tablename__ = "reports"

    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Report metadata
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    template: Mapped[str] = mapped_column(
        String(100), default=ReportTemplate.TECHNICAL.value, nullable=False
    )
    format: Mapped[str] = mapped_column(
        String(20), default=ReportFormat.PDF.value, nullable=False
    )

    # Report content configuration
    content: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    # {
    #     "sections": ["executive_summary", "methodology", "findings", "recommendations"],
    #     "include_evidence": true,
    #     "include_raw_output": false,
    #     "severity_filter": ["critical", "high", "medium"],
    #     "vulnerability_ids": [...],
    #     "asset_ids": [...],
    # }

    # Branding
    branding: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    # {
    #     "company_name": "...",
    #     "logo_url": "...",
    #     "primary_color": "#...",
    #     "footer_text": "...",
    # }

    # Generation status
    status: Mapped[str] = mapped_column(
        String(50), default=ReportStatus.PENDING.value, nullable=False
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # File storage
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(nullable=True)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Timing
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Scheduling
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cron_expression: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Creator
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="reports")
    creator: Mapped[Optional["User"]] = relationship("User")

    def __repr__(self) -> str:
        return f"<Report {self.title}>"
