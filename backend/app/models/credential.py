"""Credential model for storing discovered credentials."""

import uuid
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, JSONB, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.asset import Asset
    from app.models.job import Job


class HashType(str, Enum):
    """Hash type enumeration."""

    PLAINTEXT = "plaintext"
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    SHA512 = "sha512"
    BCRYPT = "bcrypt"
    NTLM = "ntlm"
    LM = "lm"
    MYSQL = "mysql"
    POSTGRES_MD5 = "postgres_md5"
    MSSQL = "mssql"
    ORACLE = "oracle"
    KERBEROS = "kerberos"
    UNKNOWN = "unknown"


class CredentialType(str, Enum):
    """Credential type enumeration."""

    PASSWORD = "password"
    HASH = "hash"
    API_KEY = "api_key"
    TOKEN = "token"
    SSH_KEY = "ssh_key"
    CERTIFICATE = "certificate"
    COOKIE = "cookie"
    OTHER = "other"


class Credential(Base, UUIDMixin, TimestampMixin):
    """Credential model for storing discovered credentials securely."""

    __tablename__ = "credentials"

    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Credential type
    credential_type: Mapped[str] = mapped_column(
        String(50), default=CredentialType.PASSWORD.value, nullable=False
    )

    # Credential data
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Encrypted fields (use Fernet encryption)
    password_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    plaintext_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Hash information
    hash_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hash_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Service information
    service: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    port: Mapped[Optional[int]] = mapped_column(nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Validation status
    is_valid: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    validated_at: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Source tracking
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    discovered_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )

    # Additional metadata
    metadata_: Mapped[Dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Deduplication
    fingerprint: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="credentials")
    asset: Mapped[Optional["Asset"]] = relationship("Asset", back_populates="credentials")
    discovery_job: Mapped[Optional["Job"]] = relationship(
        "Job", back_populates="discovered_credentials", foreign_keys=[discovered_by]
    )

    def __repr__(self) -> str:
        return f"<Credential {self.username}@{self.service}>"
