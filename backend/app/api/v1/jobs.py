"""Jobs API endpoints."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession, Pagination
from app.core.exceptions import BadRequestError, NotFoundError
from app.models.asset import Asset
from app.models.job import Job, JobOutput, JobStatus, JobTarget
from app.models.project import Project, ProjectMember
from app.models.result import Result
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.job import (
    JobAction,
    JobCreate,
    JobOutputListResponse,
    JobOutputResponse,
    JobResponse,
    JobTargetResponse,
    JobUpdate,
)

router = APIRouter()


@router.get("", response_model=PaginatedResponse[JobResponse])
async def list_jobs(
    current_user: CurrentUser,
    db: DbSession,
    pagination: Pagination,
    project_id: Optional[UUID] = None,
    tool_name: Optional[str] = None,
    status_filter: Optional[JobStatus] = Query(None, alias="status"),
) -> dict:
    """List jobs."""
    query = select(Job)

    # Filter by accessible projects if not superuser
    if not current_user.is_superuser:
        accessible_projects = select(ProjectMember.project_id).where(
            ProjectMember.user_id == current_user.id
        )
        created_projects = select(Project.id).where(Project.created_by == current_user.id)
        query = query.where(
            Job.project_id.in_(accessible_projects) | Job.project_id.in_(created_projects)
        )

    if project_id:
        query = query.where(Job.project_id == project_id)

    if tool_name:
        query = query.where(Job.tool_name == tool_name)

    if status_filter:
        query = query.where(Job.status == status_filter.value)

    query = query.order_by(Job.created_at.desc())

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Get paginated results
    query = query.options(
        selectinload(Job.targets).selectinload(JobTarget.asset)
    ).offset(pagination.offset).limit(pagination.page_size)

    result = await db.execute(query)
    jobs = result.scalars().unique().all()

    job_responses = []
    for job in jobs:
        result_count = await db.scalar(
            select(func.count()).select_from(Result).where(Result.job_id == job.id)
        )

        targets = [
            JobTargetResponse(
                asset_id=t.asset_id,
                asset_type=t.asset.type,
                asset_value=t.asset.value,
            )
            for t in job.targets
        ]

        job_responses.append(
            JobResponse(
                id=job.id,
                project_id=job.project_id,
                tool_name=job.tool_name,
                parameters=job.parameters,
                command=job.command,
                priority=job.priority,
                timeout_seconds=job.timeout_seconds,
                status=JobStatus(job.status),
                container_id=job.container_id,
                celery_task_id=job.celery_task_id,
                exit_code=job.exit_code,
                error_message=job.error_message,
                started_at=job.started_at,
                completed_at=job.completed_at,
                scheduled_at=job.scheduled_at,
                created_by=job.created_by,
                workflow_run_id=job.workflow_run_id,
                created_at=job.created_at,
                updated_at=job.updated_at,
                targets=targets,
                result_count=result_count or 0,
            )
        )

    return {
        "items": job_responses,
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "pages": (total + pagination.page_size - 1) // pagination.page_size if total else 0,
    }


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    data: JobCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> JobResponse:
    """Create and queue a new job."""
    # Verify project access
    result = await db.execute(select(Project).where(Project.id == data.project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise NotFoundError("Project", str(data.project_id))

    if not current_user.is_superuser:
        result = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == data.project_id,
                ProjectMember.user_id == current_user.id,
            )
        )
        if not result.scalar_one_or_none() and project.created_by != current_user.id:
            raise NotFoundError("Project", str(data.project_id))

    # Verify tool exists
    from app.tools.registry import get_tool
    tool = get_tool(data.tool_name)
    if not tool:
        raise NotFoundError("Tool", data.tool_name)

    # Build command
    command = tool.command_template
    for param in tool.parameters:
        param_value = data.parameters.get(param.name)
        placeholder = "{" + param.name + "}"
        if param_value is not None:
            command = command.replace(placeholder, str(param_value))
        else:
            command = command.replace(placeholder, str(param.default) if param.default else "")
    command = " ".join(command.split())

    # Create job
    job = Job(
        project_id=data.project_id,
        tool_name=data.tool_name,
        parameters=data.parameters,
        command=command,
        priority=data.priority,
        timeout_seconds=data.timeout_seconds,
        scheduled_at=data.scheduled_at,
        created_by=current_user.id,
        status=JobStatus.PENDING.value if not data.scheduled_at else JobStatus.QUEUED.value,
    )

    db.add(job)
    await db.flush()

    # Add targets
    targets = []
    for asset_id in data.target_asset_ids:
        result = await db.execute(select(Asset).where(Asset.id == asset_id))
        asset = result.scalar_one_or_none()
        if asset:
            target = JobTarget(job_id=job.id, asset_id=asset_id)
            db.add(target)
            targets.append(
                JobTargetResponse(
                    asset_id=asset.id,
                    asset_type=asset.type,
                    asset_value=asset.value,
                )
            )

    await db.flush()
    await db.refresh(job)

    # Queue the job if not scheduled
    if not data.scheduled_at:
        from app.services.task_queue import enqueue_task
        from app.services.tool_executor import execute_tool
        task_id = enqueue_task(execute_tool, str(job.id), task_name=f"job:{job.id}")
        job.celery_task_id = str(task_id)
        job.status = JobStatus.QUEUED.value

    return JobResponse(
        id=job.id,
        project_id=job.project_id,
        tool_name=job.tool_name,
        parameters=job.parameters,
        command=job.command,
        priority=job.priority,
        timeout_seconds=job.timeout_seconds,
        status=JobStatus(job.status),
        container_id=job.container_id,
        celery_task_id=job.celery_task_id,
        exit_code=job.exit_code,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
        scheduled_at=job.scheduled_at,
        created_by=job.created_by,
        workflow_run_id=job.workflow_run_id,
        created_at=job.created_at,
        updated_at=job.updated_at,
        targets=targets,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> JobResponse:
    """Get job by ID."""
    query = select(Job).where(Job.id == job_id).options(
        selectinload(Job.targets).selectinload(JobTarget.asset)
    )
    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        raise NotFoundError("Job", str(job_id))

    result_count = await db.scalar(
        select(func.count()).select_from(Result).where(Result.job_id == job.id)
    )

    targets = [
        JobTargetResponse(
            asset_id=t.asset_id,
            asset_type=t.asset.type,
            asset_value=t.asset.value,
        )
        for t in job.targets
    ]

    return JobResponse(
        id=job.id,
        project_id=job.project_id,
        tool_name=job.tool_name,
        parameters=job.parameters,
        command=job.command,
        priority=job.priority,
        timeout_seconds=job.timeout_seconds,
        status=JobStatus(job.status),
        container_id=job.container_id,
        celery_task_id=job.celery_task_id,
        exit_code=job.exit_code,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
        scheduled_at=job.scheduled_at,
        created_by=job.created_by,
        workflow_run_id=job.workflow_run_id,
        created_at=job.created_at,
        updated_at=job.updated_at,
        targets=targets,
        result_count=result_count or 0,
    )


@router.get("/{job_id}/output", response_model=JobOutputListResponse)
async def get_job_output(
    job_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    offset: int = 0,
    limit: int = 1000,
) -> JobOutputListResponse:
    """Get job output."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise NotFoundError("Job", str(job_id))

    # Get outputs
    query = select(JobOutput).where(JobOutput.job_id == job_id).order_by(
        JobOutput.sequence
    ).offset(offset).limit(limit + 1)

    result = await db.execute(query)
    outputs = result.scalars().all()

    has_more = len(outputs) > limit
    if has_more:
        outputs = outputs[:limit]

    return JobOutputListResponse(
        job_id=job_id,
        outputs=[
            JobOutputResponse(
                id=o.id,
                sequence=o.sequence,
                output_type=o.output_type,
                content=o.content,
                timestamp=o.timestamp,
            )
            for o in outputs
        ],
        total=len(outputs),
        has_more=has_more,
    )


@router.post("/{job_id}/action", response_model=MessageResponse)
async def job_action(
    job_id: UUID,
    data: JobAction,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Perform an action on a job (cancel, retry)."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise NotFoundError("Job", str(job_id))

    if data.action == "cancel":
        if job.status not in [JobStatus.PENDING.value, JobStatus.QUEUED.value, JobStatus.RUNNING.value]:
            raise BadRequestError("Cannot cancel job in current state")

        # Cancel the job
        from app.services.tool_executor import cancel_job_async
        import asyncio
        asyncio.create_task(cancel_job_async(str(job.id)))

        job.status = JobStatus.CANCELLED.value
        job.completed_at = datetime.utcnow()

        return {"message": "Job cancelled", "success": True}

    elif data.action == "retry":
        if job.status not in [JobStatus.FAILED.value, JobStatus.CANCELLED.value, JobStatus.TIMEOUT.value]:
            raise BadRequestError("Cannot retry job in current state")

        # Create new job with same parameters
        new_job = Job(
            project_id=job.project_id,
            tool_name=job.tool_name,
            parameters=job.parameters,
            command=job.command,
            priority=job.priority,
            timeout_seconds=job.timeout_seconds,
            created_by=current_user.id,
            status=JobStatus.QUEUED.value,
        )
        db.add(new_job)
        await db.flush()

        # Queue the job
        from app.services.task_queue import enqueue_task
        from app.services.tool_executor import execute_tool
        task_id = enqueue_task(execute_tool, str(new_job.id), task_name=f"job:{new_job.id}")
        new_job.celery_task_id = str(task_id)

        return {"message": f"Job retried, new job ID: {new_job.id}", "success": True}

    else:
        raise BadRequestError(f"Unknown action: {data.action}")


@router.delete("/{job_id}", response_model=MessageResponse)
async def delete_job(
    job_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Delete a job."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise NotFoundError("Job", str(job_id))

    if job.status == JobStatus.RUNNING.value:
        raise BadRequestError("Cannot delete a running job")

    await db.delete(job)

    return {"message": "Job deleted successfully", "success": True}
