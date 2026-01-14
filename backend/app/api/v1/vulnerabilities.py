"""Vulnerabilities API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, Pagination
from app.core.exceptions import NotFoundError
from app.models.asset import Asset
from app.models.project import Project, ProjectMember
from app.models.vulnerability import Vulnerability, VulnerabilitySeverity, VulnerabilityStatus
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.vulnerability import (
    VulnerabilityAssetInfo,
    VulnerabilityBulkUpdate,
    VulnerabilityCreate,
    VulnerabilityResponse,
    VulnerabilityStats,
    VulnerabilityUpdate,
)

router = APIRouter()


@router.get("", response_model=PaginatedResponse[VulnerabilityResponse])
async def list_vulnerabilities(
    current_user: CurrentUser,
    db: DbSession,
    pagination: Pagination,
    project_id: Optional[UUID] = None,
    severity: Optional[VulnerabilitySeverity] = None,
    status_filter: Optional[VulnerabilityStatus] = Query(None, alias="status"),
    asset_id: Optional[UUID] = None,
    search: Optional[str] = None,
) -> dict:
    """List vulnerabilities."""
    query = select(Vulnerability)

    if project_id:
        query = query.where(Vulnerability.project_id == project_id)
    elif not current_user.is_superuser:
        accessible_projects = select(ProjectMember.project_id).where(
            ProjectMember.user_id == current_user.id
        )
        created_projects = select(Project.id).where(Project.created_by == current_user.id)
        query = query.where(
            Vulnerability.project_id.in_(accessible_projects) |
            Vulnerability.project_id.in_(created_projects)
        )

    if severity:
        query = query.where(Vulnerability.severity == severity.value)

    if status_filter:
        query = query.where(Vulnerability.status == status_filter.value)

    if asset_id:
        query = query.where(Vulnerability.asset_id == asset_id)

    if search:
        query = query.where(
            Vulnerability.title.ilike(f"%{search}%") |
            Vulnerability.description.ilike(f"%{search}%")
        )

    query = query.order_by(Vulnerability.created_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    query = query.offset(pagination.offset).limit(pagination.page_size)
    result = await db.execute(query)
    vulns = result.scalars().all()

    vuln_responses = []
    for vuln in vulns:
        asset_info = None
        if vuln.asset_id:
            asset_result = await db.execute(select(Asset).where(Asset.id == vuln.asset_id))
            asset = asset_result.scalar_one_or_none()
            if asset:
                asset_info = VulnerabilityAssetInfo(
                    id=asset.id,
                    type=asset.type,
                    value=asset.value,
                )

        vuln_responses.append(
            VulnerabilityResponse(
                id=vuln.id,
                project_id=vuln.project_id,
                asset_id=vuln.asset_id,
                title=vuln.title,
                description=vuln.description,
                severity=VulnerabilitySeverity(vuln.severity),
                status=VulnerabilityStatus(vuln.status),
                cvss_score=vuln.cvss_score,
                cvss_vector=vuln.cvss_vector,
                cve_ids=vuln.cve_ids,
                cwe_ids=vuln.cwe_ids,
                evidence=vuln.evidence,
                proof_of_concept=vuln.proof_of_concept,
                request=vuln.request,
                response=vuln.response,
                remediation=vuln.remediation,
                references=vuln.references,
                tags=vuln.tags,
                discovered_by=vuln.discovered_by,
                assigned_to=vuln.assigned_to,
                template_id=vuln.template_id,
                tool_name=vuln.tool_name,
                metadata=vuln.metadata_,
                created_at=vuln.created_at,
                updated_at=vuln.updated_at,
                asset=asset_info,
            )
        )

    return {
        "items": vuln_responses,
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "pages": (total + pagination.page_size - 1) // pagination.page_size if total else 0,
    }


@router.post("", response_model=VulnerabilityResponse, status_code=status.HTTP_201_CREATED)
async def create_vulnerability(
    data: VulnerabilityCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> VulnerabilityResponse:
    """Create a new vulnerability."""
    # Handle both enum instances and string values (Pydantic v2 with use_enum_values)
    vuln_severity = data.severity.value if hasattr(data.severity, 'value') else data.severity
    vuln_status = data.status.value if hasattr(data.status, 'value') else data.status

    vuln = Vulnerability(
        project_id=data.project_id,
        asset_id=data.asset_id,
        title=data.title,
        description=data.description,
        severity=vuln_severity,
        status=vuln_status,
        cvss_score=data.cvss_score,
        cvss_vector=data.cvss_vector,
        cve_ids=data.cve_ids or [],
        cwe_ids=data.cwe_ids or [],
        evidence=data.evidence,
        proof_of_concept=data.proof_of_concept,
        request=data.request,
        response=data.response,
        remediation=data.remediation,
        references=data.references or [],
        tags=data.tags or [],
        template_id=data.template_id,
        tool_name=data.tool_name,
    )

    db.add(vuln)
    await db.flush()
    await db.refresh(vuln)

    return VulnerabilityResponse(
        id=vuln.id,
        project_id=vuln.project_id,
        asset_id=vuln.asset_id,
        title=vuln.title,
        description=vuln.description,
        severity=VulnerabilitySeverity(vuln.severity),
        status=VulnerabilityStatus(vuln.status),
        cvss_score=vuln.cvss_score,
        cvss_vector=vuln.cvss_vector,
        cve_ids=vuln.cve_ids,
        cwe_ids=vuln.cwe_ids,
        evidence=vuln.evidence,
        proof_of_concept=vuln.proof_of_concept,
        request=vuln.request,
        response=vuln.response,
        remediation=vuln.remediation,
        references=vuln.references,
        tags=vuln.tags,
        discovered_by=vuln.discovered_by,
        assigned_to=vuln.assigned_to,
        template_id=vuln.template_id,
        tool_name=vuln.tool_name,
        metadata=vuln.metadata_,
        created_at=vuln.created_at,
        updated_at=vuln.updated_at,
    )


@router.get("/stats", response_model=VulnerabilityStats)
async def get_vulnerability_stats(
    current_user: CurrentUser,
    db: DbSession,
    project_id: Optional[UUID] = None,
) -> VulnerabilityStats:
    """Get vulnerability statistics."""
    query = select(Vulnerability)

    if project_id:
        query = query.where(Vulnerability.project_id == project_id)

    # Total count
    total = await db.scalar(select(func.count()).select_from(query.subquery()))

    # By severity
    severity_query = select(
        Vulnerability.severity, func.count().label("count")
    ).group_by(Vulnerability.severity)
    if project_id:
        severity_query = severity_query.where(Vulnerability.project_id == project_id)
    result = await db.execute(severity_query)
    by_severity = {row.severity: row.count for row in result}

    # By status
    status_query = select(
        Vulnerability.status, func.count().label("count")
    ).group_by(Vulnerability.status)
    if project_id:
        status_query = status_query.where(Vulnerability.project_id == project_id)
    result = await db.execute(status_query)
    by_status = {row.status: row.count for row in result}

    return VulnerabilityStats(
        total=total or 0,
        by_severity=by_severity,
        by_status=by_status,
        by_asset_type={},
        recent_count=0,
        remediated_count=by_status.get(VulnerabilityStatus.REMEDIATED.value, 0),
    )


@router.get("/{vuln_id}", response_model=VulnerabilityResponse)
async def get_vulnerability(
    vuln_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> VulnerabilityResponse:
    """Get vulnerability by ID."""
    result = await db.execute(select(Vulnerability).where(Vulnerability.id == vuln_id))
    vuln = result.scalar_one_or_none()

    if not vuln:
        raise NotFoundError("Vulnerability", str(vuln_id))

    asset_info = None
    if vuln.asset_id:
        asset_result = await db.execute(select(Asset).where(Asset.id == vuln.asset_id))
        asset = asset_result.scalar_one_or_none()
        if asset:
            asset_info = VulnerabilityAssetInfo(id=asset.id, type=asset.type, value=asset.value)

    return VulnerabilityResponse(
        id=vuln.id,
        project_id=vuln.project_id,
        asset_id=vuln.asset_id,
        title=vuln.title,
        description=vuln.description,
        severity=VulnerabilitySeverity(vuln.severity),
        status=VulnerabilityStatus(vuln.status),
        cvss_score=vuln.cvss_score,
        cvss_vector=vuln.cvss_vector,
        cve_ids=vuln.cve_ids,
        cwe_ids=vuln.cwe_ids,
        evidence=vuln.evidence,
        proof_of_concept=vuln.proof_of_concept,
        request=vuln.request,
        response=vuln.response,
        remediation=vuln.remediation,
        references=vuln.references,
        tags=vuln.tags,
        discovered_by=vuln.discovered_by,
        assigned_to=vuln.assigned_to,
        template_id=vuln.template_id,
        tool_name=vuln.tool_name,
        metadata=vuln.metadata_,
        created_at=vuln.created_at,
        updated_at=vuln.updated_at,
        asset=asset_info,
    )


@router.patch("/{vuln_id}", response_model=VulnerabilityResponse)
async def update_vulnerability(
    vuln_id: UUID,
    data: VulnerabilityUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> VulnerabilityResponse:
    """Update a vulnerability."""
    result = await db.execute(select(Vulnerability).where(Vulnerability.id == vuln_id))
    vuln = result.scalar_one_or_none()

    if not vuln:
        raise NotFoundError("Vulnerability", str(vuln_id))

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field in ["severity", "status"] and value:
            setattr(vuln, field, value.value)
        elif hasattr(vuln, field):
            setattr(vuln, field, value)

    await db.flush()
    await db.refresh(vuln)

    return VulnerabilityResponse(
        id=vuln.id,
        project_id=vuln.project_id,
        asset_id=vuln.asset_id,
        title=vuln.title,
        description=vuln.description,
        severity=VulnerabilitySeverity(vuln.severity),
        status=VulnerabilityStatus(vuln.status),
        cvss_score=vuln.cvss_score,
        cvss_vector=vuln.cvss_vector,
        cve_ids=vuln.cve_ids,
        cwe_ids=vuln.cwe_ids,
        evidence=vuln.evidence,
        proof_of_concept=vuln.proof_of_concept,
        request=vuln.request,
        response=vuln.response,
        remediation=vuln.remediation,
        references=vuln.references,
        tags=vuln.tags,
        discovered_by=vuln.discovered_by,
        assigned_to=vuln.assigned_to,
        template_id=vuln.template_id,
        tool_name=vuln.tool_name,
        metadata=vuln.metadata_,
        created_at=vuln.created_at,
        updated_at=vuln.updated_at,
    )


@router.delete("/{vuln_id}", response_model=MessageResponse)
async def delete_vulnerability(
    vuln_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Delete a vulnerability."""
    result = await db.execute(select(Vulnerability).where(Vulnerability.id == vuln_id))
    vuln = result.scalar_one_or_none()

    if not vuln:
        raise NotFoundError("Vulnerability", str(vuln_id))

    await db.delete(vuln)

    return {"message": "Vulnerability deleted successfully", "success": True}
