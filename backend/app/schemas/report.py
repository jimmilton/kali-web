"""Report schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field

from app.models.report import ReportFormat, ReportStatus, ReportTemplate
from app.schemas.common import BaseSchema, PaginatedResponse, TimestampSchema


class ReportBranding(BaseSchema):
    """Schema for report branding configuration."""

    company_name: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    footer_text: Optional[str] = None
    header_text: Optional[str] = None
    cover_image_url: Optional[str] = None


class ReportContent(BaseSchema):
    """Schema for report content configuration."""

    sections: List[str] = [
        "executive_summary",
        "methodology",
        "scope",
        "findings",
        "recommendations",
        "appendix",
    ]
    include_evidence: bool = True
    include_raw_output: bool = False
    include_remediation: bool = True
    include_references: bool = True
    severity_filter: Optional[List[str]] = None  # ["critical", "high", "medium"]
    status_filter: Optional[List[str]] = None
    vulnerability_ids: Optional[List[UUID]] = None
    asset_ids: Optional[List[UUID]] = None
    custom_sections: Optional[List[Dict[str, Any]]] = None


class ReportBase(BaseSchema):
    """Base report schema."""

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    template: ReportTemplate = ReportTemplate.TECHNICAL
    format: ReportFormat = ReportFormat.PDF
    content: ReportContent = ReportContent()
    branding: ReportBranding = ReportBranding()


class ReportCreate(ReportBase):
    """Schema for creating a report."""

    project_id: UUID
    scheduled_at: Optional[datetime] = None
    cron_expression: Optional[str] = None


class ReportUpdate(BaseSchema):
    """Schema for updating a report."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    template: Optional[ReportTemplate] = None
    format: Optional[ReportFormat] = None
    content: Optional[ReportContent] = None
    branding: Optional[ReportBranding] = None
    scheduled_at: Optional[datetime] = None
    cron_expression: Optional[str] = None


class ReportResponse(ReportBase, TimestampSchema):
    """Schema for report response."""

    id: UUID
    project_id: UUID
    status: ReportStatus
    error_message: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
    generated_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None
    cron_expression: Optional[str] = None
    created_by: Optional[UUID] = None

    # Related data
    project_name: Optional[str] = None
    download_url: Optional[str] = None


class ReportListResponse(PaginatedResponse[ReportResponse]):
    """Paginated report list response."""

    pass


class ReportFilter(BaseSchema):
    """Schema for report filtering."""

    templates: Optional[List[ReportTemplate]] = None
    formats: Optional[List[ReportFormat]] = None
    statuses: Optional[List[ReportStatus]] = None
    created_by: Optional[UUID] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search: Optional[str] = None


class ReportGenerateRequest(BaseSchema):
    """Schema for report generation request."""

    report_id: UUID
    regenerate: bool = False


class ReportDownloadResponse(BaseSchema):
    """Schema for report download response."""

    download_url: str
    filename: str
    content_type: str
    file_size: int
    expires_at: datetime


class ReportPreview(BaseSchema):
    """Schema for report preview."""

    html_content: str
    page_count: int
    word_count: int
    vulnerability_count: int
    asset_count: int


class ReportTemplateInfo(BaseSchema):
    """Schema for report template information."""

    id: ReportTemplate
    name: str
    description: str
    sections: List[str]
    preview_image: Optional[str] = None
    sample_url: Optional[str] = None
