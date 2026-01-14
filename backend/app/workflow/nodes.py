"""Workflow node type handlers."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobStatus
from app.models.workflow import NodeType
from app.tools.registry import get_tool
from app.workflow.context import WorkflowContext

logger = logging.getLogger(__name__)


@dataclass
class NodeResult:
    """Result from executing a node."""

    success: bool
    data: dict[str, Any]
    error: str | None = None
    # For branching (condition nodes)
    branch: str | None = None
    # For parallel nodes
    children_results: list[NodeResult] | None = None


class BaseNode(ABC):
    """Base class for workflow nodes."""

    node_type: NodeType

    def __init__(self, node_data: dict, context: WorkflowContext):
        self.node_id = node_data.get("id", "")
        self.node_data = node_data.get("data", {})
        self.context = context

    @abstractmethod
    async def execute(self, db: AsyncSession) -> NodeResult:
        """Execute the node and return a result."""
        raise NotImplementedError

    def _log_entry(self, status: str, result: dict | None = None) -> dict:
        """Create an execution log entry."""
        entry = {
            "node_id": self.node_id,
            "node_type": self.node_type.value if hasattr(self.node_type, 'value') else str(self.node_type),
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if result:
            entry["result"] = result
        return entry


class ToolNode(BaseNode):
    """Execute a security tool."""

    node_type = NodeType.TOOL

    async def execute(self, db: AsyncSession) -> NodeResult:
        """Create a job and wait for it to complete."""
        tool_name = self.node_data.get("tool")
        params = self.node_data.get("parameters", {})
        timeout = self.node_data.get("timeout", 3600)

        if not tool_name:
            return NodeResult(
                success=False,
                data={},
                error="No tool specified",
            )

        # Get tool definition to validate
        tool = get_tool(tool_name)
        if not tool:
            return NodeResult(
                success=False,
                data={},
                error=f"Tool '{tool_name}' not found",
            )

        # Resolve parameter variables from context
        resolved_params = self.context.resolve_value(params)

        # Build command from template
        command = tool.command_template
        for key, value in resolved_params.items():
            placeholder = "{" + key + "}"
            if placeholder in command:
                command = command.replace(placeholder, str(value) if value else "")

        # Clean up empty placeholders
        import re
        command = re.sub(r"\{[^}]+\}", "", command)
        command = " ".join(command.split())

        # Get project_id and workflow_run_id from context
        project_id = self.context.get("project_id")
        workflow_run_id = self.context.get("workflow_run_id")

        if not project_id:
            return NodeResult(
                success=False,
                data={},
                error="No project_id in context",
            )

        # Create job
        job = Job(
            project_id=UUID(project_id) if isinstance(project_id, str) else project_id,
            tool_name=tool_name,
            parameters=resolved_params,
            command=command,
            workflow_run_id=UUID(workflow_run_id) if isinstance(workflow_run_id, str) else workflow_run_id,
            status=JobStatus.QUEUED.value,
            timeout_seconds=timeout,
        )
        db.add(job)
        await db.flush()
        await db.refresh(job)

        job_id = str(job.id)

        # Queue job execution
        from app.services.task_queue import enqueue_task
        from app.services.tool_executor import execute_tool
        enqueue_task(execute_tool, job_id, task_name=f"job:{job_id}")

        # Poll for job completion
        logger.info(f"Waiting for job {job_id} to complete")
        poll_interval = 2
        max_wait = timeout + 60  # Extra buffer beyond job timeout
        elapsed = 0

        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            # Refresh job status
            result = await db.execute(select(Job).where(Job.id == job.id))
            job = result.scalar_one_or_none()

            if not job:
                return NodeResult(
                    success=False,
                    data={"job_id": job_id},
                    error="Job disappeared",
                )

            if job.status in [
                JobStatus.COMPLETED.value,
                JobStatus.FAILED.value,
                JobStatus.CANCELLED.value,
                JobStatus.TIMEOUT.value,
            ]:
                break

        # Check final status
        if job.status == JobStatus.COMPLETED.value:
            return NodeResult(
                success=True,
                data={
                    "job_id": job_id,
                    "exit_code": job.exit_code,
                    "status": job.status,
                },
            )
        else:
            return NodeResult(
                success=False,
                data={
                    "job_id": job_id,
                    "exit_code": job.exit_code,
                    "status": job.status,
                },
                error=job.error_message or f"Job ended with status: {job.status}",
            )


class ConditionNode(BaseNode):
    """Evaluate a condition and determine branch."""

    node_type = NodeType.CONDITION

    async def execute(self, db: AsyncSession) -> NodeResult:
        """Evaluate condition and return branch result."""
        condition = self.node_data.get("condition", "")
        true_label = self.node_data.get("true_label", "true")
        false_label = self.node_data.get("false_label", "false")

        if not condition:
            return NodeResult(
                success=False,
                data={},
                error="No condition specified",
            )

        try:
            result = self.context.evaluate_condition(condition)
            branch = true_label if result else false_label

            return NodeResult(
                success=True,
                data={
                    "condition": condition,
                    "result": result,
                    "branch": branch,
                },
                branch=branch,
            )
        except Exception as e:
            return NodeResult(
                success=False,
                data={"condition": condition},
                error=str(e),
            )


class DelayNode(BaseNode):
    """Wait for a specified duration."""

    node_type = NodeType.DELAY

    async def execute(self, db: AsyncSession) -> NodeResult:
        """Wait for the specified delay."""
        delay_seconds = self.node_data.get("delay_seconds", 0)

        try:
            delay_seconds = int(delay_seconds)
        except (TypeError, ValueError):
            delay_seconds = 0

        if delay_seconds > 0:
            logger.info(f"Delay node waiting {delay_seconds} seconds")
            await asyncio.sleep(delay_seconds)

        return NodeResult(
            success=True,
            data={"delay_seconds": delay_seconds},
        )


class NotificationNode(BaseNode):
    """Send a notification via WebSocket."""

    node_type = NodeType.NOTIFICATION

    async def execute(self, db: AsyncSession) -> NodeResult:
        """Send notification via WebSocket."""
        notification_type = self.node_data.get("notification_type", "info")
        message = self.node_data.get("message", "")
        title = self.node_data.get("title", "Workflow Notification")

        # Resolve variables in message
        resolved_message = self.context.resolve_value(message)
        resolved_title = self.context.resolve_value(title)

        workflow_run_id = self.context.get("workflow_run_id")
        project_id = self.context.get("project_id")

        try:
            from app.websocket.manager import emit_project_update

            await emit_project_update(
                str(project_id),
                "workflow_notification",
                {
                    "workflow_run_id": str(workflow_run_id),
                    "type": notification_type,
                    "title": resolved_title,
                    "message": resolved_message,
                    "node_id": self.node_id,
                },
            )

            return NodeResult(
                success=True,
                data={
                    "notification_type": notification_type,
                    "message": resolved_message,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
            return NodeResult(
                success=True,  # Don't fail workflow on notification error
                data={"notification_type": notification_type},
                error=str(e),
            )


class ParallelNode(BaseNode):
    """Execute multiple child nodes in parallel."""

    node_type = NodeType.PARALLEL

    def __init__(
        self,
        node_data: dict,
        context: WorkflowContext,
        child_nodes: list[BaseNode] | None = None,
    ):
        super().__init__(node_data, context)
        self.child_nodes = child_nodes or []

    async def execute(self, db: AsyncSession) -> NodeResult:
        """Execute all child nodes in parallel."""
        if not self.child_nodes:
            return NodeResult(
                success=True,
                data={"message": "No child nodes to execute"},
            )

        max_parallel = self.node_data.get("max_parallel", 5)

        # Execute children in parallel with semaphore for throttling
        semaphore = asyncio.Semaphore(max_parallel)

        async def execute_with_semaphore(node: BaseNode) -> NodeResult:
            async with semaphore:
                return await node.execute(db)

        tasks = [execute_with_semaphore(node) for node in self.child_nodes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        children_results = []
        all_success = True
        errors = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                children_results.append(
                    NodeResult(success=False, data={}, error=str(result))
                )
                all_success = False
                errors.append(f"Child {i}: {str(result)}")
            else:
                children_results.append(result)
                if not result.success:
                    all_success = False
                    if result.error:
                        errors.append(f"Child {i}: {result.error}")

        return NodeResult(
            success=all_success,
            data={
                "children_count": len(self.child_nodes),
                "success_count": sum(1 for r in children_results if r.success),
            },
            error="; ".join(errors) if errors else None,
            children_results=children_results,
        )


class LoopNode(BaseNode):
    """Execute child nodes in a loop."""

    node_type = NodeType.LOOP

    def __init__(
        self,
        node_data: dict,
        context: WorkflowContext,
        child_executor: Callable | None = None,
    ):
        super().__init__(node_data, context)
        self.child_executor = child_executor

    async def execute(self, db: AsyncSession) -> NodeResult:
        """Execute loop iterations."""
        loop_type = self.node_data.get("loop_type", "count")
        iterations = self.node_data.get("iterations", 0)
        items = self.node_data.get("items", [])
        items_source = self.node_data.get("items_source", "")

        # Determine what to iterate over
        loop_items = []

        if loop_type == "count":
            try:
                iterations = int(iterations)
            except (TypeError, ValueError):
                iterations = 0
            loop_items = list(range(iterations))

        elif loop_type == "items":
            # Items can be a direct list or a context variable
            if items_source:
                resolved = self.context.resolve_value(f"${{{items_source}}}")
                if isinstance(resolved, list):
                    loop_items = resolved
            elif items:
                loop_items = items

        if not loop_items:
            return NodeResult(
                success=True,
                data={"iterations": 0, "message": "No items to iterate"},
            )

        if not self.child_executor:
            return NodeResult(
                success=False,
                data={},
                error="No child executor configured for loop",
            )

        # Execute iterations
        results = []
        total = len(loop_items)

        for index, item in enumerate(loop_items):
            # Set loop context
            self.context.set_loop_context(index, item, total, self.node_id)

            try:
                result = await self.child_executor(db)
                results.append(result)

                if not result.success:
                    # Check if we should continue on error
                    if not self.node_data.get("continue_on_error", False):
                        break
            except Exception as e:
                results.append(NodeResult(success=False, data={}, error=str(e)))
                if not self.node_data.get("continue_on_error", False):
                    break

        # Clear loop context
        self.context.clear_loop_context()

        success_count = sum(1 for r in results if r.success)
        all_success = success_count == len(results)

        return NodeResult(
            success=all_success,
            data={
                "iterations": len(loop_items),
                "executed": len(results),
                "success_count": success_count,
            },
            children_results=results,
        )


class ManualNode(BaseNode):
    """Wait for manual approval."""

    node_type = NodeType.MANUAL

    async def execute(self, db: AsyncSession) -> NodeResult:
        """
        Request manual approval.

        This node doesn't actually wait - the workflow engine will
        pause the workflow and wait for an API call to approve.
        """
        title = self.node_data.get("title", "Manual Approval Required")
        message = self.node_data.get("message", "Please approve to continue")
        options = self.node_data.get("options", ["approve", "reject"])

        # Resolve variables
        resolved_title = self.context.resolve_value(title)
        resolved_message = self.context.resolve_value(message)

        workflow_run_id = self.context.get("workflow_run_id")
        project_id = self.context.get("project_id")

        # Emit WebSocket notification
        try:
            from app.websocket.manager import emit_project_update

            await emit_project_update(
                str(project_id),
                "workflow_approval_required",
                {
                    "workflow_run_id": str(workflow_run_id),
                    "node_id": self.node_id,
                    "title": resolved_title,
                    "message": resolved_message,
                    "options": options,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to emit approval request: {e}")

        # Return a special result that tells the engine to pause
        return NodeResult(
            success=True,
            data={
                "approval_required": True,
                "node_id": self.node_id,
                "title": resolved_title,
                "message": resolved_message,
                "options": options,
            },
        )


def create_node(node_data: dict, context: WorkflowContext) -> BaseNode | None:
    """Factory function to create the appropriate node type."""
    node_type = node_data.get("type", "")

    node_classes = {
        "tool": ToolNode,
        "condition": ConditionNode,
        "delay": DelayNode,
        "notification": NotificationNode,
        "parallel": ParallelNode,
        "loop": LoopNode,
        "manual": ManualNode,
    }

    node_class = node_classes.get(node_type)
    if node_class:
        return node_class(node_data, context)

    logger.warning(f"Unknown node type: {node_type}")
    return None
