"""Workflows API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, Pagination
from app.core.exceptions import NotFoundError
from app.models.workflow import Workflow, WorkflowRun, WorkflowStatus
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.workflow import (
    WorkflowApprovalRequest,
    WorkflowCreate,
    WorkflowResponse,
    WorkflowRunCreate,
    WorkflowRunResponse,
    WorkflowUpdate,
)

router = APIRouter()


# Task implementations for workflow execution
async def execute_workflow_task(run_id: str) -> dict:
    """Background task to execute a workflow."""
    import logging
    from datetime import datetime

    from sqlalchemy import select

    from app.db.session import async_session
    from app.workflow.engine import WorkflowEngine

    logger = logging.getLogger(__name__)

    async with async_session() as db:
        try:
            # Load workflow run
            result = await db.execute(
                select(WorkflowRun).where(WorkflowRun.id == UUID(run_id))
            )
            run = result.scalar_one_or_none()

            if not run:
                logger.error(f"Workflow run {run_id} not found")
                return {"success": False, "error": "Workflow run not found"}

            # Load workflow definition
            workflow_result = await db.execute(
                select(Workflow).where(Workflow.id == run.workflow_id)
            )
            workflow = workflow_result.scalar_one_or_none()

            if not workflow:
                logger.error(f"Workflow {run.workflow_id} not found")
                run.status = WorkflowStatus.FAILED.value
                run.error_message = "Workflow definition not found"
                run.completed_at = datetime.utcnow()
                await db.commit()
                return {"success": False, "error": "Workflow not found"}

            # Execute workflow
            engine = WorkflowEngine(db, run, workflow)
            success = await engine.execute()

            return {"success": success, "run_id": run_id}

        except Exception as e:
            logger.exception(f"Workflow execution failed: {e}")
            return {"success": False, "error": str(e)}


async def resume_workflow_task(run_id: str, node_id: str, approval_data: dict) -> dict:
    """Background task to resume a workflow after approval."""
    import logging

    from sqlalchemy import select

    from app.db.session import async_session
    from app.workflow.engine import WorkflowEngine

    logger = logging.getLogger(__name__)

    async with async_session() as db:
        try:
            # Load workflow run
            result = await db.execute(
                select(WorkflowRun).where(WorkflowRun.id == UUID(run_id))
            )
            run = result.scalar_one_or_none()

            if not run:
                logger.error(f"Workflow run {run_id} not found")
                return {"success": False, "error": "Workflow run not found"}

            # Load workflow definition
            workflow_result = await db.execute(
                select(Workflow).where(Workflow.id == run.workflow_id)
            )
            workflow = workflow_result.scalar_one_or_none()

            if not workflow:
                logger.error(f"Workflow {run.workflow_id} not found")
                return {"success": False, "error": "Workflow not found"}

            # Resume workflow
            engine = WorkflowEngine(db, run, workflow)
            success = await engine.resume(node_id, approval_data)

            return {"success": success, "run_id": run_id}

        except Exception as e:
            logger.exception(f"Workflow resume failed: {e}")
            return {"success": False, "error": str(e)}


async def cancel_workflow_task(run_id: str) -> dict:
    """Background task to cancel a workflow."""
    import logging
    from datetime import datetime

    from sqlalchemy import select

    from app.db.session import async_session

    logger = logging.getLogger(__name__)

    async with async_session() as db:
        try:
            # Load workflow run
            result = await db.execute(
                select(WorkflowRun).where(WorkflowRun.id == UUID(run_id))
            )
            run = result.scalar_one_or_none()

            if not run:
                logger.error(f"Workflow run {run_id} not found")
                return {"success": False, "error": "Workflow run not found"}

            # Check if cancellable
            if run.status in [
                WorkflowStatus.COMPLETED.value,
                WorkflowStatus.FAILED.value,
                WorkflowStatus.CANCELLED.value,
            ]:
                return {"success": False, "error": f"Cannot cancel: status is {run.status}"}

            # Cancel the run
            run.status = WorkflowStatus.CANCELLED.value
            run.completed_at = datetime.utcnow()
            await db.commit()

            # Emit WebSocket notification
            try:
                from app.websocket.manager import emit_project_update

                await emit_project_update(
                    str(run.project_id),
                    "workflow_status",
                    {
                        "workflow_run_id": str(run.id),
                        "status": "cancelled",
                    },
                )
            except Exception as ws_error:
                logger.warning(f"Failed to emit cancellation status: {ws_error}")

            return {"success": True, "run_id": run_id}

        except Exception as e:
            logger.exception(f"Workflow cancellation failed: {e}")
            return {"success": False, "error": str(e)}


@router.get("", response_model=PaginatedResponse[WorkflowResponse])
async def list_workflows(
    current_user: CurrentUser,
    db: DbSession,
    pagination: Pagination,
    project_id: Optional[UUID] = None,
    is_template: Optional[bool] = None,
    category: Optional[str] = None,
) -> dict:
    """List workflows."""
    query = select(Workflow)

    if project_id:
        query = query.where(Workflow.project_id == project_id)
    elif is_template:
        query = query.where(Workflow.is_template.is_(True))

    if category:
        query = query.where(Workflow.category == category)

    query = query.order_by(Workflow.updated_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    query = query.offset(pagination.offset).limit(pagination.page_size)
    result = await db.execute(query)
    workflows = result.scalars().all()

    return {
        "items": [
            WorkflowResponse(
                id=w.id,
                project_id=w.project_id,
                name=w.name,
                description=w.description,
                definition=w.definition,
                is_template=w.is_template,
                is_public=w.is_public,
                category=w.category,
                tags=w.tags,
                settings=w.settings,
                created_by=w.created_by,
                created_at=w.created_at,
                updated_at=w.updated_at,
            )
            for w in workflows
        ],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "pages": (total + pagination.page_size - 1) // pagination.page_size if total else 0,
    }


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    data: WorkflowCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> WorkflowResponse:
    """Create a new workflow."""
    workflow = Workflow(
        project_id=data.project_id,
        name=data.name,
        description=data.description,
        definition=data.definition.model_dump(),
        is_template=data.is_template,
        is_public=data.is_public,
        category=data.category,
        tags=data.tags,
        settings=data.settings.model_dump(),
        created_by=current_user.id,
    )

    db.add(workflow)
    await db.flush()
    await db.refresh(workflow)

    return WorkflowResponse(
        id=workflow.id,
        project_id=workflow.project_id,
        name=workflow.name,
        description=workflow.description,
        definition=workflow.definition,
        is_template=workflow.is_template,
        is_public=workflow.is_public,
        category=workflow.category,
        tags=workflow.tags,
        settings=workflow.settings,
        created_by=workflow.created_by,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
    )


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> WorkflowResponse:
    """Get workflow by ID."""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise NotFoundError("Workflow", str(workflow_id))

    return WorkflowResponse(
        id=workflow.id,
        project_id=workflow.project_id,
        name=workflow.name,
        description=workflow.description,
        definition=workflow.definition,
        is_template=workflow.is_template,
        is_public=workflow.is_public,
        category=workflow.category,
        tags=workflow.tags,
        settings=workflow.settings,
        created_by=workflow.created_by,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
    )


@router.patch("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: UUID,
    data: WorkflowUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> WorkflowResponse:
    """Update a workflow."""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise NotFoundError("Workflow", str(workflow_id))

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "definition" and value:
            workflow.definition = value.model_dump() if hasattr(value, 'model_dump') else value
        elif field == "settings" and value:
            workflow.settings = value.model_dump() if hasattr(value, 'model_dump') else value
        elif hasattr(workflow, field):
            setattr(workflow, field, value)

    await db.flush()
    await db.refresh(workflow)

    return WorkflowResponse(
        id=workflow.id,
        project_id=workflow.project_id,
        name=workflow.name,
        description=workflow.description,
        definition=workflow.definition,
        is_template=workflow.is_template,
        is_public=workflow.is_public,
        category=workflow.category,
        tags=workflow.tags,
        settings=workflow.settings,
        created_by=workflow.created_by,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
    )


@router.delete("/{workflow_id}", response_model=MessageResponse)
async def delete_workflow(
    workflow_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Delete a workflow."""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise NotFoundError("Workflow", str(workflow_id))

    await db.delete(workflow)

    return {"message": "Workflow deleted successfully", "success": True}


@router.post("/{workflow_id}/run", response_model=WorkflowRunResponse)
async def run_workflow(
    workflow_id: UUID,
    data: WorkflowRunCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> WorkflowRunResponse:
    """Start a workflow run."""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise NotFoundError("Workflow", str(workflow_id))

    run = WorkflowRun(
        workflow_id=workflow_id,
        project_id=data.project_id,
        input_params=data.input_params,
        created_by=current_user.id,
        status=WorkflowStatus.PENDING.value,
    )

    db.add(run)
    await db.flush()
    await db.refresh(run)

    # Queue workflow execution
    from app.services.task_queue import enqueue_task
    enqueue_task(execute_workflow_task, str(run.id), task_name=f"workflow:{run.id}")

    return WorkflowRunResponse(
        id=run.id,
        workflow_id=run.workflow_id,
        project_id=run.project_id,
        status=WorkflowStatus(run.status),
        current_node_id=run.current_node_id,
        current_step=run.current_step,
        context=run.context,
        input_params=run.input_params,
        execution_log=run.execution_log,
        error_message=run.error_message,
        error_node_id=run.error_node_id,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_by=run.created_by,
        created_at=run.created_at,
        updated_at=run.updated_at,
        workflow_name=workflow.name,
    )


@router.get("/{workflow_id}/runs", response_model=PaginatedResponse[WorkflowRunResponse])
async def list_workflow_runs(
    workflow_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    pagination: Pagination,
) -> dict:
    """List workflow runs."""
    query = select(WorkflowRun).where(WorkflowRun.workflow_id == workflow_id)
    query = query.order_by(WorkflowRun.created_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    query = query.offset(pagination.offset).limit(pagination.page_size)
    result = await db.execute(query)
    runs = result.scalars().all()

    return {
        "items": [
            WorkflowRunResponse(
                id=r.id,
                workflow_id=r.workflow_id,
                project_id=r.project_id,
                status=WorkflowStatus(r.status),
                current_node_id=r.current_node_id,
                current_step=r.current_step,
                context=r.context,
                input_params=r.input_params,
                execution_log=r.execution_log,
                error_message=r.error_message,
                error_node_id=r.error_node_id,
                started_at=r.started_at,
                completed_at=r.completed_at,
                created_by=r.created_by,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in runs
        ],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "pages": (total + pagination.page_size - 1) // pagination.page_size if total else 0,
    }


@router.get("/runs/{run_id}", response_model=WorkflowRunResponse)
async def get_workflow_run(
    run_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> WorkflowRunResponse:
    """Get workflow run by ID."""
    result = await db.execute(select(WorkflowRun).where(WorkflowRun.id == run_id))
    run = result.scalar_one_or_none()

    if not run:
        raise NotFoundError("WorkflowRun", str(run_id))

    # Get workflow name
    workflow_result = await db.execute(
        select(Workflow).where(Workflow.id == run.workflow_id)
    )
    workflow = workflow_result.scalar_one_or_none()

    return WorkflowRunResponse(
        id=run.id,
        workflow_id=run.workflow_id,
        project_id=run.project_id,
        status=WorkflowStatus(run.status),
        current_node_id=run.current_node_id,
        current_step=run.current_step,
        context=run.context,
        input_params=run.input_params,
        execution_log=run.execution_log,
        error_message=run.error_message,
        error_node_id=run.error_node_id,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_by=run.created_by,
        created_at=run.created_at,
        updated_at=run.updated_at,
        workflow_name=workflow.name if workflow else None,
    )


@router.post("/runs/{run_id}/approve", response_model=WorkflowRunResponse)
async def approve_workflow_step(
    run_id: UUID,
    data: WorkflowApprovalRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> WorkflowRunResponse:
    """
    Approve a manual approval step in a workflow.

    This resumes a workflow that is waiting for approval.
    """
    result = await db.execute(select(WorkflowRun).where(WorkflowRun.id == run_id))
    run = result.scalar_one_or_none()

    if not run:
        raise NotFoundError("WorkflowRun", str(run_id))

    if run.status != WorkflowStatus.WAITING_APPROVAL.value:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Workflow is not waiting for approval (status: {run.status})"
        )

    # Get workflow name
    workflow_result = await db.execute(
        select(Workflow).where(Workflow.id == run.workflow_id)
    )
    workflow = workflow_result.scalar_one_or_none()

    # Queue resume task
    from app.services.task_queue import enqueue_task
    enqueue_task(
        resume_workflow_task,
        str(run_id),
        data.node_id,
        {
            "option": data.option,
            "comment": data.comment,
            "approved_by": str(current_user.id),
        },
        task_name=f"workflow:resume:{run_id}",
    )

    return WorkflowRunResponse(
        id=run.id,
        workflow_id=run.workflow_id,
        project_id=run.project_id,
        status=WorkflowStatus(run.status),
        current_node_id=run.current_node_id,
        current_step=run.current_step,
        context=run.context,
        input_params=run.input_params,
        execution_log=run.execution_log,
        error_message=run.error_message,
        error_node_id=run.error_node_id,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_by=run.created_by,
        created_at=run.created_at,
        updated_at=run.updated_at,
        workflow_name=workflow.name if workflow else None,
    )


@router.post("/runs/{run_id}/cancel", response_model=MessageResponse)
async def cancel_workflow_run(
    run_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Cancel a running workflow."""
    result = await db.execute(select(WorkflowRun).where(WorkflowRun.id == run_id))
    run = result.scalar_one_or_none()

    if not run:
        raise NotFoundError("WorkflowRun", str(run_id))

    if run.status in [
        WorkflowStatus.COMPLETED.value,
        WorkflowStatus.FAILED.value,
        WorkflowStatus.CANCELLED.value,
    ]:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Workflow has already finished (status: {run.status})"
        )

    # Queue cancel task
    from app.services.task_queue import enqueue_task
    enqueue_task(cancel_workflow_task, str(run_id), task_name=f"workflow:cancel:{run_id}")

    return {"message": "Workflow cancellation requested", "success": True}
