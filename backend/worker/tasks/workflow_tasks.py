"""Workflow execution tasks."""

import asyncio
import logging
from typing import Any, Dict
from uuid import UUID

from celery import shared_task
from sqlalchemy import select

from app.db.session import async_session
from app.models.workflow import Workflow, WorkflowRun, WorkflowStatus
from app.workflow.engine import WorkflowEngine

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=1)
def execute_workflow(self, workflow_run_id: str) -> Dict[str, Any]:
    """
    Execute a workflow.

    This task is queued when a workflow run is created.
    """
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_execute_workflow_async(self, workflow_run_id))


async def _execute_workflow_async(task, workflow_run_id: str) -> Dict[str, Any]:
    """Async implementation of workflow execution."""
    logger.info(f"Starting workflow execution for run {workflow_run_id}")

    async with async_session() as db:
        # Get workflow run
        result = await db.execute(
            select(WorkflowRun).where(WorkflowRun.id == UUID(workflow_run_id))
        )
        run = result.scalar_one_or_none()

        if not run:
            logger.error(f"Workflow run {workflow_run_id} not found")
            return {"error": "Workflow run not found"}

        # Get workflow definition
        result = await db.execute(
            select(Workflow).where(Workflow.id == run.workflow_id)
        )
        workflow = result.scalar_one_or_none()

        if not workflow:
            run.status = WorkflowStatus.FAILED.value
            run.error_message = "Workflow definition not found"
            await db.commit()
            return {"error": "Workflow not found"}

        # Create engine and execute
        engine = WorkflowEngine(db, run, workflow)
        success = await engine.execute()

        return {"success": success, "status": run.status}


@shared_task(bind=True)
def resume_workflow(self, workflow_run_id: str, node_id: str, approval_data: dict) -> Dict[str, Any]:
    """
    Resume a paused workflow after manual approval.

    Args:
        workflow_run_id: The workflow run to resume
        node_id: The node that was approved
        approval_data: Data from the approval (option selected, etc.)
    """
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        _resume_workflow_async(self, workflow_run_id, node_id, approval_data)
    )


async def _resume_workflow_async(
    task, workflow_run_id: str, node_id: str, approval_data: dict
) -> Dict[str, Any]:
    """Async implementation of workflow resume."""
    logger.info(f"Resuming workflow run {workflow_run_id} from node {node_id}")

    async with async_session() as db:
        # Get workflow run
        result = await db.execute(
            select(WorkflowRun).where(WorkflowRun.id == UUID(workflow_run_id))
        )
        run = result.scalar_one_or_none()

        if not run:
            logger.error(f"Workflow run {workflow_run_id} not found")
            return {"error": "Workflow run not found"}

        # Verify we're in the right state
        if run.status != WorkflowStatus.WAITING_APPROVAL.value:
            logger.error(
                f"Workflow run {workflow_run_id} is not waiting for approval "
                f"(status: {run.status})"
            )
            return {"error": "Workflow is not waiting for approval"}

        # Get workflow definition
        result = await db.execute(
            select(Workflow).where(Workflow.id == run.workflow_id)
        )
        workflow = result.scalar_one_or_none()

        if not workflow:
            run.status = WorkflowStatus.FAILED.value
            run.error_message = "Workflow definition not found"
            await db.commit()
            return {"error": "Workflow not found"}

        # Create engine and resume
        engine = WorkflowEngine(db, run, workflow)
        success = await engine.resume(node_id, approval_data)

        return {"success": success, "status": run.status}


@shared_task
def cancel_workflow(workflow_run_id: str) -> Dict[str, Any]:
    """Cancel a running workflow."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_cancel_workflow_async(workflow_run_id))


async def _cancel_workflow_async(workflow_run_id: str) -> Dict[str, Any]:
    """Async implementation of workflow cancellation."""
    logger.info(f"Cancelling workflow run {workflow_run_id}")

    async with async_session() as db:
        result = await db.execute(
            select(WorkflowRun).where(WorkflowRun.id == UUID(workflow_run_id))
        )
        run = result.scalar_one_or_none()

        if not run:
            return {"error": "Workflow run not found"}

        if run.status in [
            WorkflowStatus.COMPLETED.value,
            WorkflowStatus.FAILED.value,
            WorkflowStatus.CANCELLED.value,
        ]:
            return {"error": "Workflow already finished"}

        run.status = WorkflowStatus.CANCELLED.value
        await db.commit()

        # Emit cancellation event
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
        except Exception as e:
            logger.warning(f"Failed to emit cancellation: {e}")

        return {"success": True, "status": run.status}
