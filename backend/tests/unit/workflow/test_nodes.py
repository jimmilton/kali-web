"""Tests for workflow node types."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from app.workflow.context import WorkflowContext
from app.workflow.nodes import (
    NodeResult,
    BaseNode,
    ToolNode,
    ConditionNode,
    DelayNode,
    NotificationNode,
    ParallelNode,
    LoopNode,
    ManualNode,
    create_node,
)


class TestNodeResult:
    """Test NodeResult dataclass."""

    def test_basic_result(self):
        result = NodeResult(success=True, data={"key": "value"})
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
        assert result.branch is None

    def test_result_with_error(self):
        result = NodeResult(success=False, data={}, error="Something went wrong")
        assert result.success is False
        assert result.error == "Something went wrong"

    def test_result_with_branch(self):
        result = NodeResult(success=True, data={}, branch="true")
        assert result.branch == "true"

    def test_result_with_children(self):
        child1 = NodeResult(success=True, data={})
        child2 = NodeResult(success=True, data={})
        result = NodeResult(success=True, data={}, children_results=[child1, child2])
        assert len(result.children_results) == 2


class TestCreateNodeFactory:
    """Test create_node factory function."""

    def test_create_tool_node(self):
        ctx = WorkflowContext()
        node = create_node({"id": "n1", "type": "tool", "data": {}}, ctx)
        assert isinstance(node, ToolNode)

    def test_create_condition_node(self):
        ctx = WorkflowContext()
        node = create_node({"id": "n1", "type": "condition", "data": {}}, ctx)
        assert isinstance(node, ConditionNode)

    def test_create_delay_node(self):
        ctx = WorkflowContext()
        node = create_node({"id": "n1", "type": "delay", "data": {}}, ctx)
        assert isinstance(node, DelayNode)

    def test_create_notification_node(self):
        ctx = WorkflowContext()
        node = create_node({"id": "n1", "type": "notification", "data": {}}, ctx)
        assert isinstance(node, NotificationNode)

    def test_create_parallel_node(self):
        ctx = WorkflowContext()
        node = create_node({"id": "n1", "type": "parallel", "data": {}}, ctx)
        assert isinstance(node, ParallelNode)

    def test_create_loop_node(self):
        ctx = WorkflowContext()
        node = create_node({"id": "n1", "type": "loop", "data": {}}, ctx)
        assert isinstance(node, LoopNode)

    def test_create_manual_node(self):
        ctx = WorkflowContext()
        node = create_node({"id": "n1", "type": "manual", "data": {}}, ctx)
        assert isinstance(node, ManualNode)

    def test_create_unknown_node(self):
        ctx = WorkflowContext()
        node = create_node({"id": "n1", "type": "unknown", "data": {}}, ctx)
        assert node is None


class TestConditionNode:
    """Test ConditionNode execution."""

    @pytest.mark.asyncio
    async def test_condition_true(self):
        ctx = WorkflowContext({"status": "completed"})
        node = ConditionNode(
            {"id": "n1", "type": "condition", "data": {"condition": "status == completed"}},
            ctx
        )

        mock_db = AsyncMock()
        result = await node.execute(mock_db)

        assert result.success is True
        assert result.branch == "true"
        assert result.data["result"] is True

    @pytest.mark.asyncio
    async def test_condition_false(self):
        ctx = WorkflowContext({"status": "running"})
        node = ConditionNode(
            {"id": "n1", "type": "condition", "data": {"condition": "status == completed"}},
            ctx
        )

        mock_db = AsyncMock()
        result = await node.execute(mock_db)

        assert result.success is True
        assert result.branch == "false"
        assert result.data["result"] is False

    @pytest.mark.asyncio
    async def test_condition_custom_labels(self):
        ctx = WorkflowContext({"count": 10})
        node = ConditionNode(
            {
                "id": "n1",
                "type": "condition",
                "data": {
                    "condition": "count > 5",
                    "true_label": "high",
                    "false_label": "low"
                }
            },
            ctx
        )

        mock_db = AsyncMock()
        result = await node.execute(mock_db)

        assert result.branch == "high"

    @pytest.mark.asyncio
    async def test_condition_no_condition(self):
        ctx = WorkflowContext()
        node = ConditionNode(
            {"id": "n1", "type": "condition", "data": {}},
            ctx
        )

        mock_db = AsyncMock()
        result = await node.execute(mock_db)

        assert result.success is False
        assert "No condition specified" in result.error


class TestDelayNode:
    """Test DelayNode execution."""

    @pytest.mark.asyncio
    async def test_delay_execution(self):
        ctx = WorkflowContext()
        node = DelayNode(
            {"id": "n1", "type": "delay", "data": {"delay_seconds": 0}},
            ctx
        )

        mock_db = AsyncMock()
        result = await node.execute(mock_db)

        assert result.success is True
        assert result.data["delay_seconds"] == 0

    @pytest.mark.asyncio
    async def test_delay_invalid_value(self):
        ctx = WorkflowContext()
        node = DelayNode(
            {"id": "n1", "type": "delay", "data": {"delay_seconds": "invalid"}},
            ctx
        )

        mock_db = AsyncMock()
        result = await node.execute(mock_db)

        assert result.success is True
        assert result.data["delay_seconds"] == 0


class TestManualNode:
    """Test ManualNode execution."""

    @pytest.mark.asyncio
    async def test_manual_approval_required(self):
        ctx = WorkflowContext({
            "project_id": "test-project",
            "workflow_run_id": "test-run"
        })
        node = ManualNode(
            {
                "id": "n1",
                "type": "manual",
                "data": {
                    "title": "Approve scan",
                    "message": "Do you want to proceed?",
                    "options": ["approve", "reject"]
                }
            },
            ctx
        )

        mock_db = AsyncMock()
        result = await node.execute(mock_db)

        assert result.success is True
        assert result.data["approval_required"] is True
        assert result.data["node_id"] == "n1"
        assert result.data["options"] == ["approve", "reject"]


class TestParallelNode:
    """Test ParallelNode execution."""

    @pytest.mark.asyncio
    async def test_parallel_no_children(self):
        ctx = WorkflowContext()
        node = ParallelNode(
            {"id": "n1", "type": "parallel", "data": {}},
            ctx,
            child_nodes=[]
        )

        mock_db = AsyncMock()
        result = await node.execute(mock_db)

        assert result.success is True
        assert "No child nodes" in result.data.get("message", "")


class TestLoopNode:
    """Test LoopNode execution."""

    @pytest.mark.asyncio
    async def test_loop_no_items(self):
        ctx = WorkflowContext()
        node = LoopNode(
            {"id": "n1", "type": "loop", "data": {"loop_type": "count", "iterations": 0}},
            ctx
        )

        mock_db = AsyncMock()
        result = await node.execute(mock_db)

        assert result.success is True
        assert result.data["iterations"] == 0

    @pytest.mark.asyncio
    async def test_loop_no_executor(self):
        ctx = WorkflowContext()
        node = LoopNode(
            {"id": "n1", "type": "loop", "data": {"loop_type": "count", "iterations": 3}},
            ctx,
            child_executor=None
        )

        mock_db = AsyncMock()
        result = await node.execute(mock_db)

        assert result.success is False
        assert "No child executor" in result.error
