"""Asset and asset relationship models."""

import uuid
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, JSONB, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.job import Job
    from app.models.result import Result
    from app.models.vulnerability import Vulnerability
    from app.models.credential import Credential
    from app.models.note import Note


class AssetType(str, Enum):
    """Asset type enumeration."""

    HOST = "host"
    DOMAIN = "domain"
    SUBDOMAIN = "subdomain"
    URL = "url"
    SERVICE = "service"
    NETWORK = "network"
    ENDPOINT = "endpoint"
    CERTIFICATE = "certificate"
    TECHNOLOGY = "technology"


class AssetStatus(str, Enum):
    """Asset status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class RelationType(str, Enum):
    """Asset relation type enumeration."""

    HAS_SERVICE = "has_service"
    RESOLVES_TO = "resolves_to"
    BELONGS_TO = "belongs_to"
    HOSTS = "hosts"
    USES = "uses"
    REDIRECTS_TO = "redirects_to"


class Asset(Base, UUIDMixin, TimestampMixin):
    """Asset model for tracking discovered targets and resources."""

    __tablename__ = "assets"

    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    value: Mapped[str] = mapped_column(String(500), nullable=False)

    # Additional metadata
    metadata_: Mapped[Dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )
    # Examples:
    # For host: {"ip": "192.168.1.1", "hostname": "server.example.com", "os": "Linux"}
    # For service: {"port": 80, "protocol": "tcp", "product": "nginx", "version": "1.18.0"}
    # For domain: {"registrar": "...", "dns": {...}}

    tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default=AssetStatus.ACTIVE.value, nullable=False
    )

    # Discovery tracking
    discovered_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="assets")
    discovery_job: Mapped[Optional["Job"]] = relationship(
        "Job", back_populates="discovered_assets", foreign_keys=[discovered_by]
    )
    results: Mapped[List["Result"]] = relationship(
        "Result", back_populates="asset", cascade="all, delete-orphan"
    )
    vulnerabilities: Mapped[List["Vulnerability"]] = relationship(
        "Vulnerability", back_populates="asset", cascade="all, delete-orphan"
    )
    credentials: Mapped[List["Credential"]] = relationship(
        "Credential", back_populates="asset", cascade="all, delete-orphan"
    )
    notes: Mapped[List["Note"]] = relationship(
        "Note", back_populates="asset", cascade="all, delete-orphan"
    )

    # Self-referential relationships for asset graph
    parent_relations: Mapped[List["AssetRelation"]] = relationship(
        "AssetRelation",
        back_populates="child",
        foreign_keys="AssetRelation.child_id",
        cascade="all, delete-orphan",
    )
    child_relations: Mapped[List["AssetRelation"]] = relationship(
        "AssetRelation",
        back_populates="parent",
        foreign_keys="AssetRelation.parent_id",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # Unique constraint on project + type + value
        {"sqlite_autoincrement": True},
    )

    def __repr__(self) -> str:
        return f"<Asset {self.type}:{self.value}>"


class AssetRelation(Base):
    """Asset relationship model for tracking relationships between assets."""

    __tablename__ = "asset_relations"

    parent_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("assets.id", ondelete="CASCADE"),
        primary_key=True,
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("assets.id", ondelete="CASCADE"),
        primary_key=True,
    )
    relation_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Additional metadata about the relationship
    metadata_: Mapped[Dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )

    # Relationships
    parent: Mapped["Asset"] = relationship(
        "Asset", back_populates="child_relations", foreign_keys=[parent_id]
    )
    child: Mapped["Asset"] = relationship(
        "Asset", back_populates="parent_relations", foreign_keys=[child_id]
    )

    def __repr__(self) -> str:
        return f"<AssetRelation {self.parent_id} -> {self.child_id}>"
