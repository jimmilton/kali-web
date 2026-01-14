"""Core workflow execution engine.

Copyright 2025 milbert.ai
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import Workflow, WorkflowRun, WorkflowStatus
from app.workflow.context import WorkflowContext
from app.workflow.nodes import (
    BaseNode,
    ConditionNode,
    LoopNode,
    ManualNode,
    NodeResult,
    ParallelNode,
    create_node,
)

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """
    Workflow execution engine.

    Handles:
    - Node-based execution with graph traversal
    - Asynchronous tool execution with job tracking
    - Condition evaluation and branching
    - Parallel node execution
    - Loop iterations
    - Manual approval (pause/resume)
    """

    def __init__(self, db: AsyncSession, run: WorkflowRun, workflow: Workflow):
        self.db = db
        self.run = run
        self.workflow = workflow
        self.context = WorkflowContext(run.input_params)

        # Set up context with workflow/run info
        self.context.set("project_id", str(run.project_id))
        self.context.set("workflow_id", str(workflow.id))
        self.context.set("workflow_run_id", str(run.id))
        self.context.set("workflow_name", workflow.name)

        # Parse workflow definition
        self.definition = workflow.definition
        self.nodes = {n["id"]: n for n in self.definition.get("nodes", [])}
        self.edges = self.definition.get("edges", [])

        # Build adjacency list
        self.adjacency: dict[str, list[dict]] = {}
        for edge in self.edges:
            source = edge["source"]
            if source not in self.adjacency:
                self.adjacency[source] = []
            self.adjacency[source].append(edge)

        # Track executed nodes
        self.executed: set[str] = set()

    async def execute(self) -> bool:
        """
        Execute the workflow.

        Returns True if workflow completed successfully.
        """
        logger.info(f"Starting workflow execution for run {self.run.id}")

        # Update status to running
        self.run.status = WorkflowStatus.RUNNING.value
        self.run.started_at = datetime.utcnow()
        await self.db.commit()

        # Emit start event
        await self._emit_status("running")

        try:
            # Find start nodes (nodes with no incoming edges)
            target_nodes = {e["target"] for e in self.edges}
            start_node_ids = [
                n_id for n_id in self.nodes.keys() if n_id not in target_nodes
            ]

            if not start_node_ids:
                # Fallback: use first node
                start_node_ids = list(self.nodes.keys())[:1]

            # Execute starting from each start node
            for node_id in start_node_ids:
                result = await self._execute_node(node_id)

                # Check if we need to pause for manual approval
                if result and result.data.get("approval_required"):
                    self.run.status = WorkflowStatus.WAITING_APPROVAL.value
                    self.run.current_node_id = node_id
                    self.run.context = self.context.get_all()
                    await self.db.commit()
                    await self._emit_status("waiting_approval", {"node_id": node_id})
                    return False

                if not result or not result.success:
                    raise Exception(f"Start node {node_id} failed")

            # Workflow completed
            self.run.status = WorkflowStatus.COMPLETED.value
            self.run.completed_at = datetime.utcnow()
            self.run.context = self.context.get_all()
            await self.db.commit()

            await self._emit_status("completed")
            logger.info(f"Workflow run {self.run.id} completed successfully")
            return True

        except Exception as e:
            logger.exception(f"Workflow execution failed: {e}")
            self.run.status = WorkflowStatus.FAILED.value
            self.run.error_message = str(e)
            self.run.completed_at = datetime.utcnow()
            self.run.context = self.context.get_all()
            await self.db.commit()

            await self._emit_status("failed", {"error": str(e)})
            return False

    async def resume(self, node_id: str, approval_data: dict[str, Any]) -> bool:
        """
        Resume workflow execution after manual approval.

        Args:
            node_id: The node that was approved
            approval_data: Data from the approval (e.g., which option was selected)
        """
        logger.info(f"Resuming workflow run {self.run.id} from node {node_id}")

        # Restore context from saved state
        self.context = WorkflowContext(self.run.context)
        self.context.set("project_id", str(self.run.project_id))
        self.context.set("workflow_id", str(self.workflow.id))
        self.context.set("workflow_run_id", str(self.run.id))

        # Store approval data in context
        self.context.set(f"node_{node_id}_approval", approval_data)
        self.context.set_node_result(
            node_id,
            {"approved": True, "approval_data": approval_data},
        )

        # Mark the node as executed
        self.executed.add(node_id)

        # Update status
        self.run.status = WorkflowStatus.RUNNING.value
        await self.db.commit()
        await self._emit_status("running")

        try:
            # Continue execution from the approved node's successors
            if node_id in self.adjacency:
                for edge in self.adjacency[node_id]:
                    target_id = edge["target"]
                    result = await self._execute_node(target_id)

                    # Check for another approval node
                    if result and result.data.get("approval_required"):
                        self.run.status = WorkflowStatus.WAITING_APPROVAL.value
                        self.run.current_node_id = target_id
                        self.run.context = self.context.get_all()
                        await self.db.commit()
                        await self._emit_status(
                            "waiting_approval", {"node_id": target_id}
                        )
                        return False

            # Workflow completed
            self.run.status = WorkflowStatus.COMPLETED.value
            self.run.completed_at = datetime.utcnow()
            self.run.context = self.context.get_all()
            await self.db.commit()

            await self._emit_status("completed")
            return True

        except Exception as e:
            logger.exception(f"Workflow resume failed: {e}")
            self.run.status = WorkflowStatus.FAILED.value
            self.run.error_message = str(e)
            self.run.completed_at = datetime.utcnow()
            await self.db.commit()

            await self._emit_status("failed", {"error": str(e)})
            return False

    async def _execute_node(self, node_id: str) -> NodeResult | None:
        """Execute a single node and its successors."""
        if node_id in self.executed:
            return NodeResult(success=True, data={"skipped": True})

        node_data = self.nodes.get(node_id)
        if not node_data:
            logger.error(f"Node {node_id} not found in workflow definition")
            return None

        node = create_node(node_data, self.context)
        if not node:
            return None

        # Log execution start
        log_entry = {
            "node_id": node_id,
            "node_type": node_data.get("type"),
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
        }
        self.run.execution_log.append(log_entry)
        self.run.current_node_id = node_id
        self.run.current_step += 1
        await self.db.commit()

        await self._emit_node_status(node_id, "running")

        try:
            # Handle special node types
            if isinstance(node, ParallelNode):
                result = await self._execute_parallel_node(node_data)
            elif isinstance(node, LoopNode):
                result = await self._execute_loop_node(node_data)
            else:
                result = await node.execute(self.db)

            # Update log entry
            log_entry["status"] = "completed" if result.success else "failed"
            log_entry["completed_at"] = datetime.utcnow().isoformat()
            log_entry["result"] = result.data
            if result.error:
                log_entry["error"] = result.error

            # Update last log entry
            if self.run.execution_log:
                self.run.execution_log[-1] = log_entry
            await self.db.commit()

            # Store result in context
            self.context.set_node_result(node_id, result.data)

            # Mark as executed (unless it's an approval node that's waiting)
            if not result.data.get("approval_required"):
                self.executed.add(node_id)

            await self._emit_node_status(
                node_id, "completed" if result.success else "failed", result.data
            )

            if not result.success:
                return result

            # Check for manual approval (pause workflow)
            if result.data.get("approval_required"):
                return result

            # Handle branching for condition nodes
            if isinstance(node, ConditionNode) and result.branch:
                # Find the edge with matching label
                if node_id in self.adjacency:
                    for edge in self.adjacency[node_id]:
                        edge_label = edge.get("label", edge.get("sourceHandle", ""))
                        if edge_label == result.branch or not edge_label:
                            target_id = edge["target"]
                            child_result = await self._execute_node(target_id)
                            if child_result and child_result.data.get(
                                "approval_required"
                            ):
                                return child_result
                return result

            # Execute successor nodes
            if node_id in self.adjacency:
                for edge in self.adjacency[node_id]:
                    target_id = edge["target"]
                    child_result = await self._execute_node(target_id)

                    # Propagate approval requirement
                    if child_result and child_result.data.get("approval_required"):
                        return child_result

            return result

        except Exception as e:
            logger.exception(f"Error executing node {node_id}: {e}")
            log_entry["status"] = "failed"
            log_entry["error"] = str(e)
            log_entry["completed_at"] = datetime.utcnow().isoformat()

            if self.run.execution_log:
                self.run.execution_log[-1] = log_entry

            self.run.error_node_id = node_id
            await self.db.commit()

            await self._emit_node_status(node_id, "failed", {"error": str(e)})

            return NodeResult(success=False, data={}, error=str(e))

    async def _execute_parallel_node(self, node_data: dict) -> NodeResult:
        """Execute a parallel node with its children."""
        # Find child nodes connected to this parallel node
        node_id = node_data["id"]
        child_node_ids = []

        if node_id in self.adjacency:
            for edge in self.adjacency[node_id]:
                child_node_ids.append(edge["target"])

        if not child_node_ids:
            return NodeResult(success=True, data={"message": "No child nodes"})

        max_parallel = node_data.get("data", {}).get("max_parallel", 5)
        semaphore = asyncio.Semaphore(max_parallel)

        async def execute_child(child_id: str) -> NodeResult:
            async with semaphore:
                result = await self._execute_node(child_id)
                return result or NodeResult(success=False, data={}, error="No result")

        tasks = [execute_child(child_id) for child_id in child_node_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check results
        all_success = True
        errors = []
        approval_required = False

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                all_success = False
                errors.append(str(result))
            elif isinstance(result, NodeResult):
                if not result.success:
                    all_success = False
                    if result.error:
                        errors.append(result.error)
                if result.data.get("approval_required"):
                    approval_required = True

        # Mark this node as executed
        self.executed.add(node_id)

        return NodeResult(
            success=all_success and not approval_required,
            data={
                "children_count": len(child_node_ids),
                "success_count": len([r for r in results if isinstance(r, NodeResult) and r.success]),
                "approval_required": approval_required,
            },
            error="; ".join(errors) if errors else None,
        )

    async def _execute_loop_node(self, node_data: dict) -> NodeResult:
        """Execute a loop node with iterations."""
        node_id = node_data["id"]
        data = node_data.get("data", {})

        loop_type = data.get("loop_type", "count")
        iterations = data.get("iterations", 0)
        items_source = data.get("items_source", "")
        items = data.get("items", [])
        continue_on_error = data.get("continue_on_error", False)

        # Determine loop items
        loop_items = []
        if loop_type == "count":
            try:
                loop_items = list(range(int(iterations)))
            except (TypeError, ValueError):
                pass
        elif loop_type == "items":
            if items_source:
                resolved = self.context.resolve_value(f"${{{items_source}}}")
                if isinstance(resolved, list):
                    loop_items = resolved
            elif items:
                loop_items = items

        if not loop_items:
            self.executed.add(node_id)
            return NodeResult(
                success=True, data={"iterations": 0, "message": "No items"}
            )

        # Find child nodes to execute in each iteration
        child_node_ids = []
        if node_id in self.adjacency:
            for edge in self.adjacency[node_id]:
                # Only include edges that are marked as loop body
                if edge.get("label") == "body" or edge.get("sourceHandle") == "body":
                    child_node_ids.append(edge["target"])
                elif not edge.get("label") and not edge.get("sourceHandle"):
                    child_node_ids.append(edge["target"])

        results = []
        total = len(loop_items)

        for index, item in enumerate(loop_items):
            # Set loop context
            self.context.set_loop_context(index, item, total, node_id)

            # Reset executed state for child nodes (so they run again)
            for child_id in child_node_ids:
                self.executed.discard(child_id)

            # Execute children
            iteration_success = True
            for child_id in child_node_ids:
                result = await self._execute_node(child_id)
                if result:
                    if result.data.get("approval_required"):
                        # Can't handle approval in loop - fail
                        self.context.clear_loop_context()
                        return NodeResult(
                            success=False,
                            data={},
                            error="Manual approval nodes not supported in loops",
                        )
                    if not result.success:
                        iteration_success = False
                        if not continue_on_error:
                            break

            results.append(iteration_success)
            if not iteration_success and not continue_on_error:
                break

        self.context.clear_loop_context()
        self.executed.add(node_id)

        success_count = sum(1 for r in results if r)
        all_success = success_count == len(results)

        # Execute post-loop successors
        if node_id in self.adjacency:
            for edge in self.adjacency[node_id]:
                label = edge.get("label", edge.get("sourceHandle", ""))
                if label == "done" or label == "complete":
                    target_id = edge["target"]
                    await self._execute_node(target_id)

        return NodeResult(
            success=all_success,
            data={
                "iterations": total,
                "executed": len(results),
                "success_count": success_count,
            },
        )

    async def _emit_status(
        self, status: str, details: dict[str, Any] | None = None
    ) -> None:
        """Emit workflow status via WebSocket."""
        try:
            from app.websocket.manager import emit_project_update

            await emit_project_update(
                str(self.run.project_id),
                "workflow_status",
                {
                    "workflow_run_id": str(self.run.id),
                    "workflow_id": str(self.workflow.id),
                    "status": status,
                    "details": details or {},
                },
            )
        except Exception as e:
            logger.warning(f"Failed to emit workflow status: {e}")

    async def _emit_node_status(
        self, node_id: str, status: str, data: dict[str, Any] | None = None
    ) -> None:
        """Emit node execution status via WebSocket."""
        try:
            from app.websocket.manager import emit_project_update

            await emit_project_update(
                str(self.run.project_id),
                "workflow_node_status",
                {
                    "workflow_run_id": str(self.run.id),
                    "node_id": node_id,
                    "status": status,
                    "data": data or {},
                },
            )
        except Exception as e:
            logger.warning(f"Failed to emit node status: {e}")
