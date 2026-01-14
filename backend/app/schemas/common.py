"""Common schemas used across the application."""

from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict


T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
    )


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""

    created_at: datetime
    updated_at: datetime


class PaginatedResponse(BaseSchema, Generic[T]):
    """Generic paginated response schema."""

    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1


class MessageResponse(BaseSchema):
    """Simple message response schema."""

    message: str
    success: bool = True


class ErrorResponse(BaseSchema):
    """Error response schema."""

    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class HealthResponse(BaseSchema):
    """Health check response schema."""

    status: str
    version: str
    database: Optional[str] = None
    redis: Optional[str] = None
    timestamp: datetime = None

    def __init__(self, **data):
        if "timestamp" not in data:
            data["timestamp"] = datetime.utcnow()
        super().__init__(**data)


class BulkOperationResult(BaseSchema):
    """Result of a bulk operation."""

    success_count: int
    failure_count: int
    errors: List[dict] = []


class FilterParams(BaseSchema):
    """Common filter parameters."""

    search: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: str = "desc"
    page: int = 1
    page_size: int = 20


class DateRange(BaseSchema):
    """Date range filter."""

    start: Optional[datetime] = None
    end: Optional[datetime] = None
