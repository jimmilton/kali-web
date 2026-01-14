"""Result model for storing parsed tool outputs."""

import uuid
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, JSONB, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.asset import Asset


class ResultType(str, Enum):
    """Result type enumeration."""

    PORT = "port"
    SERVICE = "service"
    VULNERABILITY = "vulnerability"
    CREDENTIAL = "credential"
    FILE = "file"
    DIRECTORY = "directory"
    SUBDOMAIN = "subdomain"
    TECHNOLOGY = "technology"
    CERTIFICATE = "certificate"
    DNS_RECORD = "dns_record"
    HEADER = "header"
    PARAMETER = "parameter"
    ENDPOINT = "endpoint"
    RAW = "raw"


class Severity(str, Enum):
    """Severity level enumeration."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Result(Base, UUIDMixin, TimestampMixin):
    """Result model for storing parsed tool output data."""

    __tablename__ = "results"

    job_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True
    )

    result_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Raw output data
    raw_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Parsed structured data
    parsed_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    # Examples:
    # Port: {"port": 80, "protocol": "tcp", "state": "open", "service": "http"}
    # Subdomain: {"subdomain": "api.example.com", "ip": "1.2.3.4", "source": "subfinder"}
    # Technology: {"name": "nginx", "version": "1.18.0", "categories": ["web-servers"]}

    # Deduplication key
    fingerprint: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="results")
    asset: Mapped[Optional["Asset"]] = relationship("Asset", back_populates="results")

    def __repr__(self) -> str:
        return f"<Result {self.result_type} job={self.job_id}>"
