"""Reports API endpoints.

Copyright 2025 milbert.ai
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, Pagination
from app.config import settings
from app.core.exceptions import NotFoundError
from app.models.report import Report, ReportFormat, ReportStatus, ReportTemplate
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.report import (
    ReportCreate,
    ReportDownloadResponse,
    ReportPreview,
    ReportResponse,
    ReportTemplateInfo,
    ReportUpdate,
)

router = APIRouter()


@router.get("", response_model=PaginatedResponse[ReportResponse])
async def list_reports(
    current_user: CurrentUser,
    db: DbSession,
    pagination: Pagination,
    project_id: Optional[UUID] = None,
    template: Optional[ReportTemplate] = None,
    status_filter: Optional[ReportStatus] = Query(None, alias="status"),
) -> dict:
    """List reports."""
    query = select(Report)

    if project_id:
        query = query.where(Report.project_id == project_id)

    if template:
        query = query.where(Report.template == template.value)

    if status_filter:
        query = query.where(Report.status == status_filter.value)

    query = query.order_by(Report.created_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    query = query.offset(pagination.offset).limit(pagination.page_size)
    result = await db.execute(query)
    reports = result.scalars().all()

    return {
        "items": [
            ReportResponse(
                id=r.id,
                project_id=r.project_id,
                title=r.title,
                description=r.description,
                template=ReportTemplate(r.template),
                format=ReportFormat(r.format),
                content=r.content,
                branding=r.branding,
                status=ReportStatus(r.status),
                error_message=r.error_message,
                file_path=r.file_path,
                file_size=r.file_size,
                file_hash=r.file_hash,
                generated_at=r.generated_at,
                scheduled_at=r.scheduled_at,
                cron_expression=r.cron_expression,
                created_by=r.created_by,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in reports
        ],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "pages": (total + pagination.page_size - 1) // pagination.page_size if total else 0,
    }


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    data: ReportCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> ReportResponse:
    """Create a new report."""
    report = Report(
        project_id=data.project_id,
        title=data.title,
        description=data.description,
        template=data.template.value,
        format=data.format.value,
        content=data.content.model_dump(),
        branding=data.branding.model_dump(),
        scheduled_at=data.scheduled_at,
        cron_expression=data.cron_expression,
        created_by=current_user.id,
        status=ReportStatus.PENDING.value,
    )

    db.add(report)
    await db.flush()
    await db.refresh(report)

    return ReportResponse(
        id=report.id,
        project_id=report.project_id,
        title=report.title,
        description=report.description,
        template=ReportTemplate(report.template),
        format=ReportFormat(report.format),
        content=report.content,
        branding=report.branding,
        status=ReportStatus(report.status),
        error_message=report.error_message,
        file_path=report.file_path,
        file_size=report.file_size,
        file_hash=report.file_hash,
        generated_at=report.generated_at,
        scheduled_at=report.scheduled_at,
        cron_expression=report.cron_expression,
        created_by=report.created_by,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> ReportResponse:
    """Get report by ID."""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()

    if not report:
        raise NotFoundError("Report", str(report_id))

    return ReportResponse(
        id=report.id,
        project_id=report.project_id,
        title=report.title,
        description=report.description,
        template=ReportTemplate(report.template),
        format=ReportFormat(report.format),
        content=report.content,
        branding=report.branding,
        status=ReportStatus(report.status),
        error_message=report.error_message,
        file_path=report.file_path,
        file_size=report.file_size,
        file_hash=report.file_hash,
        generated_at=report.generated_at,
        scheduled_at=report.scheduled_at,
        cron_expression=report.cron_expression,
        created_by=report.created_by,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


@router.post("/{report_id}/generate", response_model=MessageResponse)
async def generate_report(
    report_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Generate a report."""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()

    if not report:
        raise NotFoundError("Report", str(report_id))

    report.status = ReportStatus.GENERATING.value
    await db.flush()

    # Queue report generation using embedded task queue
    from app.services.task_queue import enqueue_task
    enqueue_task(generate_report_task, str(report_id), task_name=f"report:{report_id}")

    return {"message": "Report generation started", "success": True}


async def generate_report_task(report_id: str) -> dict:
    """Background task to generate a report."""
    import logging
    from datetime import datetime

    from sqlalchemy import select

    from app.db.session import async_session
    from app.services.report_generator import ReportGenerator

    logger = logging.getLogger(__name__)

    async with async_session() as db:
        try:
            # Load report
            result = await db.execute(
                select(Report).where(Report.id == UUID(report_id))
            )
            report = result.scalar_one_or_none()

            if not report:
                logger.error(f"Report {report_id} not found")
                return {"success": False, "error": "Report not found"}

            # Update status to generating
            report.status = ReportStatus.GENERATING.value
            await db.commit()

            # Generate report
            generator = ReportGenerator(db, report)
            content, size, file_hash, filename = await generator.generate()

            # Ensure reports directory exists
            reports_dir = settings.reports_path
            reports_dir.mkdir(parents=True, exist_ok=True)

            # Save file
            file_path = reports_dir / filename
            file_path.write_bytes(content)

            # Update report record
            report.file_path = filename
            report.file_size = size
            report.file_hash = file_hash
            report.status = ReportStatus.COMPLETED.value
            report.generated_at = datetime.utcnow()
            report.error_message = None
            await db.commit()

            # Emit WebSocket notification
            try:
                from app.websocket.manager import emit_project_update

                await emit_project_update(
                    str(report.project_id),
                    "report_generated",
                    {
                        "report_id": str(report.id),
                        "title": report.title,
                        "status": "completed",
                        "file_size": size,
                    },
                )
            except Exception as ws_error:
                logger.warning(f"Failed to emit report status: {ws_error}")

            logger.info(f"Report {report_id} generated successfully: {filename}")
            return {"success": True, "file_path": filename, "file_size": size}

        except Exception as e:
            logger.exception(f"Report generation failed: {e}")

            # Update report with error status
            try:
                result = await db.execute(
                    select(Report).where(Report.id == UUID(report_id))
                )
                report = result.scalar_one_or_none()
                if report:
                    report.status = ReportStatus.FAILED.value
                    report.error_message = str(e)
                    await db.commit()
            except Exception:
                pass

            return {"success": False, "error": str(e)}


@router.delete("/{report_id}", response_model=MessageResponse)
async def delete_report(
    report_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Delete a report."""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()

    if not report:
        raise NotFoundError("Report", str(report_id))

    # Delete file from filesystem if exists
    if report.file_path:
        try:
            file_path = settings.reports_path / report.file_path
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass  # Ignore deletion errors

    await db.delete(report)

    return {"message": "Report deleted successfully", "success": True}


def _get_content_type(report_format: str) -> str:
    """Get MIME type for report format."""
    content_types = {
        ReportFormat.PDF.value: "application/pdf",
        ReportFormat.DOCX.value: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ReportFormat.HTML.value: "text/html",
        ReportFormat.MARKDOWN.value: "text/markdown",
        ReportFormat.JSON.value: "application/json",
    }
    return content_types.get(report_format, "application/octet-stream")


def _get_file_extension(report_format: str) -> str:
    """Get file extension for report format."""
    extensions = {
        ReportFormat.PDF.value: "pdf",
        ReportFormat.DOCX.value: "docx",
        ReportFormat.HTML.value: "html",
        ReportFormat.MARKDOWN.value: "md",
        ReportFormat.JSON.value: "json",
    }
    return extensions.get(report_format, "bin")


@router.get("/{report_id}/download", response_model=ReportDownloadResponse)
async def get_download_url(
    report_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> ReportDownloadResponse:
    """Get download information for the report."""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()

    if not report:
        raise NotFoundError("Report", str(report_id))

    if report.status != ReportStatus.COMPLETED.value or not report.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report has not been generated yet",
        )

    extension = _get_file_extension(report.format)
    safe_title = "".join(c if c.isalnum() or c in "-_ " else "_" for c in report.title)
    filename = f"{safe_title}.{extension}"

    # Return direct download URL
    download_url = f"/api/v1/reports/{report_id}/stream"

    return ReportDownloadResponse(
        download_url=download_url,
        filename=filename,
        content_type=_get_content_type(report.format),
        file_size=report.file_size or 0,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )


@router.get("/{report_id}/stream")
async def stream_report(
    report_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> FileResponse:
    """Stream the report file directly."""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()

    if not report:
        raise NotFoundError("Report", str(report_id))

    if report.status != ReportStatus.COMPLETED.value or not report.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report has not been generated yet",
        )

    file_path = settings.reports_path / report.file_path
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file not found",
        )

    extension = _get_file_extension(report.format)
    safe_title = "".join(c if c.isalnum() or c in "-_ " else "_" for c in report.title)
    filename = f"{safe_title}.{extension}"

    return FileResponse(
        path=str(file_path),
        media_type=_get_content_type(report.format),
        filename=filename,
    )


@router.get("/templates/list", response_model=list[ReportTemplateInfo])
async def list_templates(
    current_user: CurrentUser,
) -> list[ReportTemplateInfo]:
    """List available report templates."""
    templates = [
        ReportTemplateInfo(
            id=ReportTemplate.EXECUTIVE,
            name="Executive Summary",
            description="High-level overview for executive stakeholders with risk scores and key findings",
            sections=["executive_summary", "recommendations"],
        ),
        ReportTemplateInfo(
            id=ReportTemplate.TECHNICAL,
            name="Technical Report",
            description="Detailed technical report with all findings, evidence, and remediation steps",
            sections=["executive_summary", "methodology", "scope", "findings", "recommendations", "appendix"],
        ),
        ReportTemplateInfo(
            id=ReportTemplate.COMPLIANCE,
            name="Compliance Report",
            description="Compliance-focused report with control assessments and attestation",
            sections=["executive_summary", "compliance_score", "findings", "remediation"],
        ),
        ReportTemplateInfo(
            id=ReportTemplate.VULNERABILITY,
            name="Vulnerability Report",
            description="Focused vulnerability listing with detailed technical information",
            sections=["summary", "findings"],
        ),
        ReportTemplateInfo(
            id=ReportTemplate.ASSET,
            name="Asset Inventory",
            description="Complete inventory of discovered assets organized by type",
            sections=["summary", "assets"],
        ),
        ReportTemplateInfo(
            id=ReportTemplate.CUSTOM,
            name="Custom Report",
            description="Customizable report with user-defined sections",
            sections=[],
        ),
    ]
    return templates


@router.put("/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: UUID,
    data: ReportUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> ReportResponse:
    """Update a report configuration."""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()

    if not report:
        raise NotFoundError("Report", str(report_id))

    # Only allow updates if report hasn't been generated or is pending
    if report.status == ReportStatus.GENERATING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update report while it is being generated",
        )

    # Update fields
    if data.title is not None:
        report.title = data.title
    if data.description is not None:
        report.description = data.description
    if data.template is not None:
        report.template = data.template.value
    if data.format is not None:
        report.format = data.format.value
    if data.content is not None:
        report.content = data.content.model_dump()
    if data.branding is not None:
        report.branding = data.branding.model_dump()
    if data.scheduled_at is not None:
        report.scheduled_at = data.scheduled_at
    if data.cron_expression is not None:
        report.cron_expression = data.cron_expression

    # Reset status if configuration changed
    if report.status == ReportStatus.COMPLETED.value:
        report.status = ReportStatus.PENDING.value

    await db.flush()
    await db.refresh(report)

    return ReportResponse(
        id=report.id,
        project_id=report.project_id,
        title=report.title,
        description=report.description,
        template=ReportTemplate(report.template),
        format=ReportFormat(report.format),
        content=report.content,
        branding=report.branding,
        status=ReportStatus(report.status),
        error_message=report.error_message,
        file_path=report.file_path,
        file_size=report.file_size,
        file_hash=report.file_hash,
        generated_at=report.generated_at,
        scheduled_at=report.scheduled_at,
        cron_expression=report.cron_expression,
        created_by=report.created_by,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )
