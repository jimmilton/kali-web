"""Report generation tasks."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from io import BytesIO
from typing import Any
from uuid import UUID

from celery import shared_task
from minio import Minio
from sqlalchemy import select

from app.config import settings
from app.db.session import async_session
from app.models.report import Report, ReportFormat, ReportStatus
from app.services.report_generator import ReportGenerator

logger = logging.getLogger(__name__)


def get_minio_client() -> Minio:
    """Get MinIO client instance."""
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def ensure_bucket_exists(client: Minio, bucket_name: str) -> None:
    """Ensure the bucket exists, create if not."""
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)


def get_content_type(report_format: str) -> str:
    """Get MIME type for report format."""
    content_types = {
        ReportFormat.PDF.value: "application/pdf",
        ReportFormat.DOCX.value: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ReportFormat.HTML.value: "text/html",
        ReportFormat.MARKDOWN.value: "text/markdown",
        ReportFormat.JSON.value: "application/json",
    }
    return content_types.get(report_format, "application/octet-stream")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_report(self, report_id: str) -> dict[str, Any]:
    """Generate a report asynchronously."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_generate_report_async(self, report_id))
    finally:
        loop.close()


async def _generate_report_async(task, report_id: str) -> dict[str, Any]:
    """Async implementation of report generation."""
    logger.info(f"Starting report generation for {report_id}")

    async with async_session() as db:
        result = await db.execute(select(Report).where(Report.id == UUID(report_id)))
        report = result.scalar_one_or_none()

        if not report:
            logger.error(f"Report {report_id} not found")
            return {"error": "Report not found", "success": False}

        # Update status to generating
        report.status = ReportStatus.GENERATING.value
        await db.commit()

        try:
            # Initialize the report generator
            generator = ReportGenerator(db, report)

            # Generate the report content
            content, file_size, file_hash, filename = await generator.generate()

            # Upload to MinIO
            minio_client = get_minio_client()
            bucket_name = settings.minio_bucket
            ensure_bucket_exists(minio_client, bucket_name)

            object_name = f"reports/{report.project_id}/{filename}"
            content_type = get_content_type(report.format)

            minio_client.put_object(
                bucket_name,
                object_name,
                BytesIO(content),
                length=file_size,
                content_type=content_type,
            )

            # Update report with file info
            report.status = ReportStatus.COMPLETED.value
            report.generated_at = datetime.now(timezone.utc)
            report.file_path = f"{bucket_name}/{object_name}"
            report.file_size = file_size
            report.file_hash = file_hash
            report.error_message = None
            await db.commit()

            logger.info(f"Report {report_id} generated successfully: {object_name}")

            # Emit WebSocket notification
            await _emit_report_notification(report_id, "completed", object_name)

            return {
                "success": True,
                "report_id": report_id,
                "file_path": object_name,
                "file_size": file_size,
            }

        except Exception as e:
            logger.exception(f"Report generation failed: {e}")
            report.status = ReportStatus.FAILED.value
            report.error_message = str(e)
            await db.commit()

            # Emit failure notification
            await _emit_report_notification(report_id, "failed", str(e))

            # Retry on transient errors
            if "connection" in str(e).lower() or "timeout" in str(e).lower():
                raise task.retry(exc=e)

            return {"error": str(e), "success": False}


async def _emit_report_notification(
    report_id: str, status: str, message: str
) -> None:
    """Emit WebSocket notification for report status."""
    try:
        from app.websocket.manager import manager

        await manager.emit(
            "report_status",
            {
                "report_id": report_id,
                "status": status,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception as e:
        logger.warning(f"Failed to emit report notification: {e}")


@shared_task(bind=True)
def schedule_report_generation(self, report_id: str) -> dict[str, Any]:
    """Check if a scheduled report needs generation."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_check_scheduled_report(report_id))
    finally:
        loop.close()


async def _check_scheduled_report(report_id: str) -> dict[str, Any]:
    """Check if scheduled report should be generated."""
    async with async_session() as db:
        result = await db.execute(select(Report).where(Report.id == UUID(report_id)))
        report = result.scalar_one_or_none()

        if not report:
            return {"error": "Report not found"}

        if report.scheduled_at and report.scheduled_at <= datetime.now(timezone.utc):
            # Time to generate
            generate_report.delay(report_id)
            return {"message": "Report generation scheduled"}

        return {"message": "Not yet time to generate"}


@shared_task
def cleanup_old_reports(days: int = 90) -> dict[str, Any]:
    """Clean up old generated reports from storage."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_cleanup_old_reports(days))
    finally:
        loop.close()


async def _cleanup_old_reports(days: int) -> dict[str, Any]:
    """Remove reports older than specified days."""
    from datetime import timedelta

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    deleted_count = 0

    async with async_session() as db:
        result = await db.execute(
            select(Report).where(
                Report.generated_at < cutoff_date,
                Report.file_path.isnot(None),
            )
        )
        old_reports = result.scalars().all()

        minio_client = get_minio_client()
        bucket_name = settings.minio_bucket

        for report in old_reports:
            try:
                if report.file_path:
                    # Extract object name from file path
                    object_name = report.file_path.replace(f"{bucket_name}/", "")
                    minio_client.remove_object(bucket_name, object_name)
                    report.file_path = None
                    report.file_size = None
                    report.file_hash = None
                    deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete report file: {e}")

        await db.commit()

    logger.info(f"Cleaned up {deleted_count} old reports")
    return {"deleted": deleted_count}
