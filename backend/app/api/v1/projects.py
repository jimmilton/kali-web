"""Projects API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession, Pagination, ProjectPermissionDependency
from app.core.exceptions import ConflictError, NotFoundError
from app.core.permissions import Permission
from app.models.asset import Asset
from app.models.job import Job
from app.models.project import Project, ProjectMember, ProjectRole
from app.models.user import User
from app.models.vulnerability import Vulnerability
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.project import (
    ProjectCreate,
    ProjectMemberCreate,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectStats,
    ProjectUpdate,
)

router = APIRouter()


async def get_project_stats(db: AsyncSession, project_id: UUID) -> ProjectStats:
    """Get statistics for a project."""
    # Count assets
    asset_count = await db.scalar(
        select(func.count()).select_from(Asset).where(Asset.project_id == project_id)
    )

    # Count jobs
    job_count = await db.scalar(
        select(func.count()).select_from(Job).where(Job.project_id == project_id)
    )

    # Count vulnerabilities by severity
    vuln_query = select(
        Vulnerability.severity,
        func.count().label("count")
    ).where(
        Vulnerability.project_id == project_id
    ).group_by(Vulnerability.severity)

    result = await db.execute(vuln_query)
    vulns_by_severity = {row.severity: row.count for row in result}

    total_vulns = sum(vulns_by_severity.values())

    return ProjectStats(
        total_assets=asset_count or 0,
        total_jobs=job_count or 0,
        total_vulnerabilities=total_vulns,
        vulnerabilities_by_severity=vulns_by_severity,
    )


@router.get("", response_model=PaginatedResponse[ProjectResponse])
async def list_projects(
    current_user: CurrentUser,
    db: DbSession,
    pagination: Pagination,
    search: Optional[str] = None,
    status: Optional[str] = None,
) -> dict:
    """List projects accessible by the current user."""
    # Build base query
    if current_user.is_superuser:
        query = select(Project)
    else:
        # Get projects where user is a member or creator
        query = select(Project).where(
            (Project.created_by == current_user.id) |
            (Project.id.in_(
                select(ProjectMember.project_id).where(
                    ProjectMember.user_id == current_user.id
                )
            ))
        )

    if search:
        query = query.where(
            (Project.name.ilike(f"%{search}%")) |
            (Project.description.ilike(f"%{search}%"))
        )

    if status:
        query = query.where(Project.status == status)

    # Order by updated_at
    query = query.order_by(Project.updated_at.desc())

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Get paginated results with members
    query = query.options(
        selectinload(Project.members).selectinload(ProjectMember.user)
    ).offset(pagination.offset).limit(pagination.page_size)

    result = await db.execute(query)
    projects = result.scalars().unique().all()

    # Add stats to each project
    project_responses = []
    for project in projects:
        stats = await get_project_stats(db, project.id)
        members = [
            ProjectMemberResponse(
                user_id=m.user.id,
                username=m.user.username,
                email=m.user.email,
                role=ProjectRole(m.role),
                full_name=m.user.full_name,
                avatar_url=m.user.avatar_url,
            )
            for m in project.members
        ]

        project_responses.append(
            ProjectResponse(
                id=project.id,
                name=project.name,
                description=project.description,
                status=project.status,
                scope=project.scope,
                settings=project.settings,
                created_by=project.created_by,
                created_at=project.created_at,
                updated_at=project.updated_at,
                members=members,
                stats=stats,
            )
        )

    return {
        "items": project_responses,
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "pages": (total + pagination.page_size - 1) // pagination.page_size if total else 0,
    }


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> ProjectResponse:
    """Create a new project."""
    # Handle both enum instances and string values (Pydantic v2 with use_enum_values)
    project_status = data.status.value if hasattr(data.status, 'value') else data.status

    project = Project(
        name=data.name,
        description=data.description,
        status=project_status,
        scope=data.scope.model_dump() if data.scope else None,
        settings=data.settings,
        created_by=current_user.id,
    )

    db.add(project)
    await db.flush()

    # Add creator as owner
    member = ProjectMember(
        project_id=project.id,
        user_id=current_user.id,
        role=ProjectRole.OWNER.value,
    )
    db.add(member)

    await db.flush()
    await db.refresh(project)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status,
        scope=project.scope,
        settings=project.settings,
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
        members=[
            ProjectMemberResponse(
                user_id=current_user.id,
                username=current_user.username,
                email=current_user.email,
                role=ProjectRole.OWNER,
                full_name=current_user.full_name,
                avatar_url=current_user.avatar_url,
            )
        ],
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> ProjectResponse:
    """Get a project by ID."""
    query = select(Project).where(Project.id == project_id).options(
        selectinload(Project.members).selectinload(ProjectMember.user)
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise NotFoundError("Project", str(project_id))

    # Check access
    if not current_user.is_superuser:
        is_member = any(m.user_id == current_user.id for m in project.members)
        is_creator = project.created_by == current_user.id
        if not is_member and not is_creator:
            raise NotFoundError("Project", str(project_id))

    stats = await get_project_stats(db, project.id)
    members = [
        ProjectMemberResponse(
            user_id=m.user.id,
            username=m.user.username,
            email=m.user.email,
            role=ProjectRole(m.role),
            full_name=m.user.full_name,
            avatar_url=m.user.avatar_url,
        )
        for m in project.members
    ]

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status,
        scope=project.scope,
        settings=project.settings,
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
        members=members,
        stats=stats,
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> ProjectResponse:
    """Update a project."""
    result = await db.execute(
        select(Project).where(Project.id == project_id).options(
            selectinload(Project.members).selectinload(ProjectMember.user)
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise NotFoundError("Project", str(project_id))

    # Check permission (owner, manager, or admin)
    if not current_user.is_superuser:
        membership = next(
            (m for m in project.members if m.user_id == current_user.id),
            None
        )
        if not membership or membership.role not in [ProjectRole.OWNER.value, ProjectRole.MANAGER.value]:
            if project.created_by != current_user.id:
                raise NotFoundError("Project", str(project_id))

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "scope" and value:
            setattr(project, field, value.model_dump() if hasattr(value, 'model_dump') else value)
        elif field == "status" and value:
            setattr(project, field, value.value if hasattr(value, 'value') else value)
        elif hasattr(project, field):
            setattr(project, field, value)

    await db.flush()
    await db.refresh(project)

    stats = await get_project_stats(db, project.id)
    members = [
        ProjectMemberResponse(
            user_id=m.user.id,
            username=m.user.username,
            email=m.user.email,
            role=ProjectRole(m.role),
            full_name=m.user.full_name,
            avatar_url=m.user.avatar_url,
        )
        for m in project.members
    ]

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status,
        scope=project.scope,
        settings=project.settings,
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
        members=members,
        stats=stats,
    )


@router.delete("/{project_id}", response_model=MessageResponse)
async def delete_project(
    project_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Delete a project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise NotFoundError("Project", str(project_id))

    # Only owner or admin can delete
    if not current_user.is_superuser and project.created_by != current_user.id:
        raise NotFoundError("Project", str(project_id))

    await db.delete(project)

    return {"message": "Project deleted successfully", "success": True}


@router.post("/{project_id}/members", response_model=ProjectMemberResponse)
async def add_project_member(
    project_id: UUID,
    data: ProjectMemberCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> ProjectMemberResponse:
    """Add a member to a project."""
    # Check project exists and user has permission
    result = await db.execute(
        select(Project).where(Project.id == project_id).options(
            selectinload(Project.members)
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise NotFoundError("Project", str(project_id))

    # Check permission
    if not current_user.is_superuser:
        membership = next(
            (m for m in project.members if m.user_id == current_user.id),
            None
        )
        if not membership or membership.role not in [ProjectRole.OWNER.value, ProjectRole.MANAGER.value]:
            raise NotFoundError("Project", str(project_id))

    # Check if user exists
    result = await db.execute(select(User).where(User.id == data.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise NotFoundError("User", str(data.user_id))

    # Check if already a member
    existing = next((m for m in project.members if m.user_id == data.user_id), None)
    if existing:
        raise ConflictError("User is already a member of this project")

    # Handle both enum instances and string values (Pydantic v2 with use_enum_values)
    member_role = data.role.value if hasattr(data.role, 'value') else data.role

    member = ProjectMember(
        project_id=project_id,
        user_id=data.user_id,
        role=member_role,
    )
    db.add(member)
    await db.flush()

    return ProjectMemberResponse(
        user_id=user.id,
        username=user.username,
        email=user.email,
        role=data.role,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
    )


@router.delete("/{project_id}/members/{user_id}", response_model=MessageResponse)
async def remove_project_member(
    project_id: UUID,
    user_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Remove a member from a project."""
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise NotFoundError("Project member")

    # Check permission (can't remove owner, only owner/manager can remove others)
    if member.role == ProjectRole.OWNER.value:
        raise ConflictError("Cannot remove the project owner")

    if not current_user.is_superuser and user_id != current_user.id:
        result = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == current_user.id,
            )
        )
        current_membership = result.scalar_one_or_none()
        if not current_membership or current_membership.role not in [
            ProjectRole.OWNER.value,
            ProjectRole.MANAGER.value,
        ]:
            raise NotFoundError("Project member")

    await db.delete(member)

    return {"message": "Member removed successfully", "success": True}
