"""Dashboard analytics API endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.asset import Asset
from app.models.credential import Credential
from app.models.job import Job, JobStatus
from app.models.project import Project
from app.models.vulnerability import Vulnerability, VulnerabilitySeverity
from app.schemas.common import BaseSchema

router = APIRouter()


class DashboardStats(BaseSchema):
    """Overall dashboard statistics."""

    projects: int
    assets: int
    vulnerabilities: int
    credentials: int
    jobs_completed: int
    jobs_running: int
    jobs_failed: int


class VulnerabilitySummary(BaseSchema):
    """Vulnerability summary by severity."""

    critical: int
    high: int
    medium: int
    low: int
    info: int
    total: int


class TrendDataPoint(BaseSchema):
    """Data point for trend charts."""

    date: str
    value: int
    label: str | None = None


class ProjectSummary(BaseSchema):
    """Summary for a project."""

    id: UUID
    name: str
    status: str
    asset_count: int
    vulnerability_count: int
    last_activity: datetime | None


class AnalyticsDashboard(BaseSchema):
    """Complete dashboard analytics response."""

    stats: DashboardStats
    vulnerability_summary: VulnerabilitySummary
    vulnerability_trends: list[TrendDataPoint]
    asset_trends: list[TrendDataPoint]
    job_trends: list[TrendDataPoint]
    recent_projects: list[ProjectSummary]
    vulnerability_by_status: dict[str, int]
    asset_by_type: dict[str, int]
    top_vulnerabilities: list[dict[str, Any]]


@router.get("/dashboard", response_model=AnalyticsDashboard)
async def get_dashboard_analytics(
    current_user: CurrentUser,
    db: DbSession,
    project_id: UUID | None = None,
    days: int = Query(30, ge=1, le=365),
) -> AnalyticsDashboard:
    """
    Get comprehensive dashboard analytics.

    Includes stats, trends, and summaries for the dashboard.
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    # Base query filters
    project_filter = Project.id == project_id if project_id else True
    asset_filter = Asset.project_id == project_id if project_id else True
    vuln_filter = Vulnerability.project_id == project_id if project_id else True
    job_filter = Job.project_id == project_id if project_id else True
    cred_filter = Credential.project_id == project_id if project_id else True

    # Get basic counts
    project_count = await db.scalar(
        select(func.count()).select_from(Project).where(project_filter)
    ) or 0

    asset_count = await db.scalar(
        select(func.count()).select_from(Asset).where(asset_filter)
    ) or 0

    vuln_count = await db.scalar(
        select(func.count()).select_from(Vulnerability).where(vuln_filter)
    ) or 0

    cred_count = await db.scalar(
        select(func.count()).select_from(Credential).where(cred_filter)
    ) or 0

    jobs_completed = await db.scalar(
        select(func.count()).select_from(Job).where(
            and_(job_filter, Job.status == JobStatus.COMPLETED.value)
        )
    ) or 0

    jobs_running = await db.scalar(
        select(func.count()).select_from(Job).where(
            and_(job_filter, Job.status.in_([JobStatus.RUNNING.value, JobStatus.PENDING.value]))
        )
    ) or 0

    jobs_failed = await db.scalar(
        select(func.count()).select_from(Job).where(
            and_(job_filter, Job.status == JobStatus.FAILED.value)
        )
    ) or 0

    # Vulnerability summary by severity
    vuln_by_severity = await db.execute(
        select(
            Vulnerability.severity,
            func.count().label("count"),
        )
        .where(vuln_filter)
        .group_by(Vulnerability.severity)
    )
    severity_counts = {row[0]: row[1] for row in vuln_by_severity}

    vuln_summary = VulnerabilitySummary(
        critical=severity_counts.get("critical", 0),
        high=severity_counts.get("high", 0),
        medium=severity_counts.get("medium", 0),
        low=severity_counts.get("low", 0),
        info=severity_counts.get("info", 0),
        total=vuln_count,
    )

    # Vulnerability trends (daily counts)
    vuln_trends = await _get_daily_trends(
        db, Vulnerability, Vulnerability.created_at, vuln_filter, cutoff_date, days
    )

    # Asset trends
    asset_trends = await _get_daily_trends(
        db, Asset, Asset.created_at, asset_filter, cutoff_date, days
    )

    # Job trends
    job_trends = await _get_daily_trends(
        db, Job, Job.created_at, job_filter, cutoff_date, days
    )

    # Vulnerability by status
    vuln_by_status = await db.execute(
        select(
            Vulnerability.status,
            func.count().label("count"),
        )
        .where(vuln_filter)
        .group_by(Vulnerability.status)
    )
    status_counts = {row[0]: row[1] for row in vuln_by_status}

    # Asset by type
    asset_by_type = await db.execute(
        select(
            Asset.type,
            func.count().label("count"),
        )
        .where(asset_filter)
        .group_by(Asset.type)
    )
    type_counts = {row[0]: row[1] for row in asset_by_type}

    # Recent projects
    recent_projects_query = (
        select(Project)
        .where(project_filter)
        .order_by(Project.updated_at.desc())
        .limit(5)
    )
    recent_projects_result = await db.execute(recent_projects_query)
    recent_projects = []

    for project in recent_projects_result.scalars().all():
        # Get counts for each project
        p_assets = await db.scalar(
            select(func.count()).select_from(Asset).where(Asset.project_id == project.id)
        ) or 0
        p_vulns = await db.scalar(
            select(func.count()).select_from(Vulnerability).where(Vulnerability.project_id == project.id)
        ) or 0

        recent_projects.append(
            ProjectSummary(
                id=project.id,
                name=project.name,
                status=project.status,
                asset_count=p_assets,
                vulnerability_count=p_vulns,
                last_activity=project.updated_at,
            )
        )

    # Top vulnerabilities (critical/high)
    top_vulns_result = await db.execute(
        select(Vulnerability)
        .where(
            and_(
                vuln_filter,
                Vulnerability.severity.in_(["critical", "high"]),
            )
        )
        .options(selectinload(Vulnerability.asset))
        .order_by(
            case(
                (Vulnerability.severity == "critical", 1),
                (Vulnerability.severity == "high", 2),
                else_=3,
            ),
            Vulnerability.created_at.desc(),
        )
        .limit(10)
    )

    top_vulnerabilities = [
        {
            "id": str(v.id),
            "title": v.title,
            "severity": v.severity,
            "status": v.status,
            "cvss_score": float(v.cvss_score) if v.cvss_score else None,
            "asset": v.asset.value if v.asset else None,
            "created_at": v.created_at.isoformat(),
        }
        for v in top_vulns_result.scalars().all()
    ]

    return AnalyticsDashboard(
        stats=DashboardStats(
            projects=project_count,
            assets=asset_count,
            vulnerabilities=vuln_count,
            credentials=cred_count,
            jobs_completed=jobs_completed,
            jobs_running=jobs_running,
            jobs_failed=jobs_failed,
        ),
        vulnerability_summary=vuln_summary,
        vulnerability_trends=vuln_trends,
        asset_trends=asset_trends,
        job_trends=job_trends,
        recent_projects=recent_projects,
        vulnerability_by_status=status_counts,
        asset_by_type=type_counts,
        top_vulnerabilities=top_vulnerabilities,
    )


async def _get_daily_trends(
    db,
    model,
    date_field,
    filter_condition,
    cutoff_date: datetime,
    days: int,
) -> list[TrendDataPoint]:
    """Get daily trend data for a model."""
    from app.config import settings

    # Use database-appropriate date truncation
    if settings.database_url.startswith("sqlite"):
        # SQLite uses date() function
        date_expr = func.date(date_field)
    else:
        # PostgreSQL uses date_trunc
        date_expr = func.date_trunc("day", date_field)

    result = await db.execute(
        select(
            date_expr.label("date"),
            func.count().label("count"),
        )
        .where(and_(filter_condition, date_field >= cutoff_date))
        .group_by(date_expr)
        .order_by(date_expr)
    )

    trends = []
    for row in result:
        if row[0]:
            # Handle both string (SQLite) and datetime (PostgreSQL) results
            if isinstance(row[0], str):
                date_str = row[0]
            else:
                date_str = row[0].strftime("%Y-%m-%d")
            trends.append(
                TrendDataPoint(
                    date=date_str,
                    value=row[1],
                )
            )

    return trends


@router.get("/vulnerability-stats")
async def get_vulnerability_stats(
    current_user: CurrentUser,
    db: DbSession,
    project_id: UUID | None = None,
) -> dict:
    """Get detailed vulnerability statistics."""
    filter_condition = Vulnerability.project_id == project_id if project_id else True

    # By severity
    by_severity = await db.execute(
        select(
            Vulnerability.severity,
            func.count().label("count"),
        )
        .where(filter_condition)
        .group_by(Vulnerability.severity)
    )

    # By status
    by_status = await db.execute(
        select(
            Vulnerability.status,
            func.count().label("count"),
        )
        .where(filter_condition)
        .group_by(Vulnerability.status)
    )

    # By tool
    by_tool = await db.execute(
        select(
            Vulnerability.tool_name,
            func.count().label("count"),
        )
        .where(and_(filter_condition, Vulnerability.tool_name.isnot(None)))
        .group_by(Vulnerability.tool_name)
    )

    # CVSS distribution
    cvss_ranges = await db.execute(
        select(
            case(
                (Vulnerability.cvss_score >= 9.0, "Critical (9.0-10.0)"),
                (Vulnerability.cvss_score >= 7.0, "High (7.0-8.9)"),
                (Vulnerability.cvss_score >= 4.0, "Medium (4.0-6.9)"),
                (Vulnerability.cvss_score >= 0.1, "Low (0.1-3.9)"),
                else_="None",
            ).label("range"),
            func.count().label("count"),
        )
        .where(filter_condition)
        .group_by("range")
    )

    return {
        "by_severity": {row[0]: row[1] for row in by_severity},
        "by_status": {row[0]: row[1] for row in by_status},
        "by_tool": {row[0]: row[1] for row in by_tool},
        "cvss_distribution": {row[0]: row[1] for row in cvss_ranges},
    }


@router.get("/asset-stats")
async def get_asset_stats(
    current_user: CurrentUser,
    db: DbSession,
    project_id: UUID | None = None,
) -> dict:
    """Get detailed asset statistics."""
    filter_condition = Asset.project_id == project_id if project_id else True

    # By type
    by_type = await db.execute(
        select(
            Asset.type,
            func.count().label("count"),
        )
        .where(filter_condition)
        .group_by(Asset.type)
    )

    # By status
    by_status = await db.execute(
        select(
            Asset.status,
            func.count().label("count"),
        )
        .where(filter_condition)
        .group_by(Asset.status)
    )

    # Risk score distribution
    risk_ranges = await db.execute(
        select(
            case(
                (Asset.risk_score >= 80, "Critical (80-100)"),
                (Asset.risk_score >= 60, "High (60-79)"),
                (Asset.risk_score >= 40, "Medium (40-59)"),
                (Asset.risk_score >= 20, "Low (20-39)"),
                else_="Minimal (0-19)",
            ).label("range"),
            func.count().label("count"),
        )
        .where(filter_condition)
        .group_by("range")
    )

    # Assets with most vulnerabilities
    top_risky = await db.execute(
        select(
            Asset.id,
            Asset.value,
            Asset.type,
            func.count(Vulnerability.id).label("vuln_count"),
        )
        .join(Vulnerability, Asset.id == Vulnerability.asset_id, isouter=True)
        .where(filter_condition)
        .group_by(Asset.id, Asset.value, Asset.type)
        .order_by(func.count(Vulnerability.id).desc())
        .limit(10)
    )

    return {
        "by_type": {row[0]: row[1] for row in by_type},
        "by_status": {row[0]: row[1] for row in by_status},
        "risk_distribution": {row[0]: row[1] for row in risk_ranges},
        "top_risky_assets": [
            {"id": str(row[0]), "value": row[1], "type": row[2], "vulnerability_count": row[3]}
            for row in top_risky
        ],
    }


@router.get("/job-stats")
async def get_job_stats(
    current_user: CurrentUser,
    db: DbSession,
    project_id: UUID | None = None,
    days: int = Query(30, ge=1, le=365),
) -> dict:
    """Get detailed job statistics."""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    filter_condition = Job.project_id == project_id if project_id else True

    # By status
    by_status = await db.execute(
        select(
            Job.status,
            func.count().label("count"),
        )
        .where(filter_condition)
        .group_by(Job.status)
    )

    # By tool
    by_tool = await db.execute(
        select(
            Job.tool_name,
            func.count().label("count"),
        )
        .where(filter_condition)
        .group_by(Job.tool_name)
        .order_by(func.count().desc())
        .limit(10)
    )

    # Average execution time by tool
    avg_duration = await db.execute(
        select(
            Job.tool_name,
            func.avg(
                func.extract("epoch", Job.completed_at - Job.started_at)
            ).label("avg_seconds"),
        )
        .where(
            and_(
                filter_condition,
                Job.completed_at.isnot(None),
                Job.started_at.isnot(None),
            )
        )
        .group_by(Job.tool_name)
    )

    # Jobs per day trend - use database-appropriate date function
    from app.config import settings
    if settings.database_url.startswith("sqlite"):
        date_expr = func.date(Job.created_at)
    else:
        date_expr = func.date_trunc("day", Job.created_at)

    daily_jobs = await db.execute(
        select(
            date_expr.label("date"),
            func.count().label("count"),
        )
        .where(and_(filter_condition, Job.created_at >= cutoff_date))
        .group_by(date_expr)
        .order_by(date_expr)
    )

    daily_trend = []
    for row in daily_jobs:
        if row[0]:
            if isinstance(row[0], str):
                date_str = row[0]
            else:
                date_str = row[0].strftime("%Y-%m-%d")
            daily_trend.append({"date": date_str, "count": row[1]})

    return {
        "by_status": {row[0]: row[1] for row in by_status},
        "by_tool": {row[0]: row[1] for row in by_tool},
        "avg_duration_by_tool": {
            row[0]: round(row[1], 2) if row[1] else None
            for row in avg_duration
        },
        "daily_trend": daily_trend,
    }
