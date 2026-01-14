"""Note model for adding comments to resources."""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, JSONB, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.asset import Asset
    from app.models.vulnerability import Vulnerability
    from app.models.user import User


class Note(Base, UUIDMixin, TimestampMixin):
    """Note model for adding comments and notes to resources."""

    __tablename__ = "notes"

    # Parent references (at least one should be set)
    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("assets.id", ondelete="CASCADE"), nullable=True, index=True
    )
    vulnerability_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("vulnerabilities.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Note content (supports markdown)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Author
    author_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="notes")
    asset: Mapped[Optional["Asset"]] = relationship("Asset", back_populates="notes")
    vulnerability: Mapped[Optional["Vulnerability"]] = relationship("Vulnerability", back_populates="notes")
    author: Mapped[Optional["User"]] = relationship("User")

    def __repr__(self) -> str:
        return f"<Note {self.id}>"
