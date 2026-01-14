"""Advanced search API endpoints."""
from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession, Pagination
from app.models.asset import Asset
from app.models.credential import Credential
from app.models.job import Job
from app.models.project import Project
from app.models.vulnerability import Vulnerability
from app.schemas.common import BaseSchema, PaginatedResponse

router = APIRouter()


class SearchEntityType(str, Enum):
    """Searchable entity types."""

    ALL = "all"
    ASSETS = "assets"
    VULNERABILITIES = "vulnerabilities"
    CREDENTIALS = "credentials"
    JOBS = "jobs"
    PROJECTS = "projects"


class SearchResult(BaseSchema):
    """Individual search result."""

    id: UUID
    type: str
    title: str
    subtitle: str | None = None
    description: str | None = None
    project_id: UUID | None = None
    project_name: str | None = None
    metadata: dict[str, Any] = {}
    score: float = 1.0
    highlight: str | None = None


class SearchResponse(BaseSchema):
    """Search response with results and facets."""

    query: str
    total: int
    results: list[SearchResult]
    facets: dict[str, dict[str, int]] = {}
    page: int
    page_size: int
    pages: int


class SearchFilters(BaseSchema):
    """Advanced search filters."""

    entity_types: list[SearchEntityType] = [SearchEntityType.ALL]
    project_ids: list[UUID] | None = None
    severity: list[str] | None = None
    status: list[str] | None = None
    asset_types: list[str] | None = None
    date_from: str | None = None
    date_to: str | None = None
    tags: list[str] | None = None


@router.get("", response_model=SearchResponse)
async def search(
    current_user: CurrentUser,
    db: DbSession,
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    entity_type: SearchEntityType = SearchEntityType.ALL,
    project_id: UUID | None = None,
    severity: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> SearchResponse:
    """
    Advanced search across all entities.

    Searches assets, vulnerabilities, credentials, jobs, and projects.
    """
    results: list[SearchResult] = []
    facets: dict[str, dict[str, int]] = {
        "entity_type": {},
        "severity": {},
        "status": {},
    }
    search_pattern = f"%{q}%"
    offset = (page - 1) * page_size

    # Search Assets
    if entity_type in [SearchEntityType.ALL, SearchEntityType.ASSETS]:
        asset_query = select(Asset).where(
            or_(
                Asset.value.ilike(search_pattern),
                Asset.type.ilike(search_pattern),
                func.cast(Asset.metadata_, String).ilike(search_pattern),
            )
        )
        if project_id:
            asset_query = asset_query.where(Asset.project_id == project_id)

        asset_result = await db.execute(asset_query.options(selectinload(Asset.project)))
        assets = asset_result.scalars().all()

        for asset in assets:
            results.append(
                SearchResult(
                    id=asset.id,
                    type="asset",
                    title=asset.value,
                    subtitle=asset.type,
                    description=f"Status: {asset.status}",
                    project_id=asset.project_id,
                    project_name=asset.project.name if asset.project else None,
                    metadata={
                        "asset_type": asset.type,
                        "status": asset.status,
                        "risk_score": asset.risk_score,
                        "tags": asset.tags,
                    },
                )
            )
        facets["entity_type"]["assets"] = len(assets)

    # Search Vulnerabilities
    if entity_type in [SearchEntityType.ALL, SearchEntityType.VULNERABILITIES]:
        vuln_query = select(Vulnerability).where(
            or_(
                Vulnerability.title.ilike(search_pattern),
                Vulnerability.description.ilike(search_pattern),
                Vulnerability.severity.ilike(search_pattern),
                func.array_to_string(Vulnerability.cve_ids, ",").ilike(search_pattern),
            )
        )
        if project_id:
            vuln_query = vuln_query.where(Vulnerability.project_id == project_id)
        if severity:
            vuln_query = vuln_query.where(Vulnerability.severity == severity)
        if status:
            vuln_query = vuln_query.where(Vulnerability.status == status)

        vuln_result = await db.execute(vuln_query.options(selectinload(Vulnerability.project)))
        vulns = vuln_result.scalars().all()

        for vuln in vulns:
            results.append(
                SearchResult(
                    id=vuln.id,
                    type="vulnerability",
                    title=vuln.title,
                    subtitle=f"{vuln.severity.upper()} - {vuln.status}",
                    description=vuln.description[:200] if vuln.description else None,
                    project_id=vuln.project_id,
                    project_name=vuln.project.name if vuln.project else None,
                    metadata={
                        "severity": vuln.severity,
                        "status": vuln.status,
                        "cvss_score": float(vuln.cvss_score) if vuln.cvss_score else None,
                        "cve_ids": vuln.cve_ids,
                    },
                )
            )
            # Update facets
            facets["severity"][vuln.severity] = facets["severity"].get(vuln.severity, 0) + 1
            facets["status"][vuln.status] = facets["status"].get(vuln.status, 0) + 1

        facets["entity_type"]["vulnerabilities"] = len(vulns)

    # Search Credentials
    if entity_type in [SearchEntityType.ALL, SearchEntityType.CREDENTIALS]:
        cred_query = select(Credential).where(
            or_(
                Credential.username.ilike(search_pattern),
                Credential.domain.ilike(search_pattern),
                Credential.service.ilike(search_pattern),
                Credential.url.ilike(search_pattern),
            )
        )
        if project_id:
            cred_query = cred_query.where(Credential.project_id == project_id)

        cred_result = await db.execute(cred_query.options(selectinload(Credential.project)))
        creds = cred_result.scalars().all()

        for cred in creds:
            results.append(
                SearchResult(
                    id=cred.id,
                    type="credential",
                    title=f"{cred.username or 'Unknown'}@{cred.service or 'Unknown'}",
                    subtitle=cred.credential_type,
                    description=f"Domain: {cred.domain}" if cred.domain else None,
                    project_id=cred.project_id,
                    project_name=cred.project.name if cred.project else None,
                    metadata={
                        "credential_type": cred.credential_type,
                        "service": cred.service,
                        "is_valid": cred.is_valid,
                    },
                )
            )
        facets["entity_type"]["credentials"] = len(creds)

    # Search Jobs
    if entity_type in [SearchEntityType.ALL, SearchEntityType.JOBS]:
        job_query = select(Job).where(
            or_(
                Job.tool_name.ilike(search_pattern),
                Job.status.ilike(search_pattern),
                func.cast(Job.parameters, String).ilike(search_pattern),
            )
        )
        if project_id:
            job_query = job_query.where(Job.project_id == project_id)
        if status:
            job_query = job_query.where(Job.status == status)

        job_result = await db.execute(job_query.options(selectinload(Job.project)))
        jobs = job_result.scalars().all()

        for job in jobs:
            results.append(
                SearchResult(
                    id=job.id,
                    type="job",
                    title=f"{job.tool_name} Job",
                    subtitle=job.status,
                    description=f"Created: {job.created_at.strftime('%Y-%m-%d %H:%M')}",
                    project_id=job.project_id,
                    project_name=job.project.name if job.project else None,
                    metadata={
                        "tool_name": job.tool_name,
                        "status": job.status,
                        "exit_code": job.exit_code,
                    },
                )
            )
        facets["entity_type"]["jobs"] = len(jobs)

    # Search Projects
    if entity_type in [SearchEntityType.ALL, SearchEntityType.PROJECTS]:
        proj_query = select(Project).where(
            or_(
                Project.name.ilike(search_pattern),
                Project.description.ilike(search_pattern),
            )
        )
        if status:
            proj_query = proj_query.where(Project.status == status)

        proj_result = await db.execute(proj_query)
        projects = proj_result.scalars().all()

        for project in projects:
            results.append(
                SearchResult(
                    id=project.id,
                    type="project",
                    title=project.name,
                    subtitle=project.status,
                    description=project.description[:200] if project.description else None,
                    project_id=project.id,
                    project_name=project.name,
                    metadata={
                        "status": project.status,
                    },
                )
            )
        facets["entity_type"]["projects"] = len(projects)

    # Sort results by relevance (simple: exact matches first)
    def sort_key(r: SearchResult) -> tuple:
        exact_match = q.lower() in r.title.lower()
        return (not exact_match, r.type)

    results.sort(key=sort_key)

    # Paginate
    total = len(results)
    paginated_results = results[offset : offset + page_size]

    return SearchResponse(
        query=q,
        total=total,
        results=paginated_results,
        facets=facets,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total else 0,
    )


# Need String import for func.cast
from sqlalchemy import String


@router.get("/suggestions")
async def search_suggestions(
    current_user: CurrentUser,
    db: DbSession,
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(10, ge=1, le=50),
) -> list[dict]:
    """
    Get search suggestions based on partial query.

    Returns quick suggestions for autocomplete.
    """
    suggestions = []
    search_pattern = f"{q}%"

    # Asset values
    asset_result = await db.execute(
        select(Asset.value, Asset.type)
        .where(Asset.value.ilike(search_pattern))
        .distinct()
        .limit(limit)
    )
    for value, asset_type in asset_result:
        suggestions.append({
            "text": value,
            "type": "asset",
            "category": asset_type,
        })

    # Vulnerability titles
    vuln_result = await db.execute(
        select(Vulnerability.title, Vulnerability.severity)
        .where(Vulnerability.title.ilike(search_pattern))
        .distinct()
        .limit(limit)
    )
    for title, severity in vuln_result:
        suggestions.append({
            "text": title,
            "type": "vulnerability",
            "category": severity,
        })

    # Project names
    proj_result = await db.execute(
        select(Project.name)
        .where(Project.name.ilike(search_pattern))
        .distinct()
        .limit(limit)
    )
    for (name,) in proj_result:
        suggestions.append({
            "text": name,
            "type": "project",
            "category": None,
        })

    # Tool names from jobs
    job_result = await db.execute(
        select(Job.tool_name)
        .where(Job.tool_name.ilike(search_pattern))
        .distinct()
        .limit(limit)
    )
    for (tool_name,) in job_result:
        suggestions.append({
            "text": tool_name,
            "type": "tool",
            "category": None,
        })

    return suggestions[:limit]


@router.get("/recent")
async def recent_searches(
    current_user: CurrentUser,
    limit: int = Query(10, ge=1, le=50),
) -> list[dict]:
    """
    Get recent search history for the user.

    Note: This is a placeholder - actual implementation would
    require storing search history in database or Redis.
    """
    # Placeholder - would typically fetch from user's search history
    return []
