"""Tests for workflow context management."""

import pytest

from app.workflow.context import WorkflowContext


class TestWorkflowContext:
    """Test WorkflowContext class."""

    def test_init_with_params(self):
        ctx = WorkflowContext({"target": "192.168.1.1", "port": 80})
        assert ctx.get("target") == "192.168.1.1"
        assert ctx.get("port") == 80

    def test_init_empty(self):
        ctx = WorkflowContext()
        assert ctx.get("nonexistent") is None
        assert ctx.get("nonexistent", "default") == "default"

    def test_set_and_get(self):
        ctx = WorkflowContext()
        ctx.set("key", "value")
        assert ctx.get("key") == "value"

    def test_update(self):
        ctx = WorkflowContext()
        ctx.update({"a": 1, "b": 2, "c": 3})
        assert ctx.get("a") == 1
        assert ctx.get("b") == 2
        assert ctx.get("c") == 3

    def test_get_all(self):
        ctx = WorkflowContext({"x": 1})
        ctx.set("y", 2)
        all_data = ctx.get_all()
        assert all_data == {"x": 1, "y": 2}

    def test_node_result(self):
        ctx = WorkflowContext()
        ctx.set_node_result("node1", {"exit_code": 0, "output": "success"})

        result = ctx.get_node_result("node1")
        assert result["exit_code"] == 0
        assert result["output"] == "success"


class TestConditionEvaluation:
    """Test condition evaluation."""

    def test_equality(self):
        ctx = WorkflowContext({"status": "completed", "code": 0})

        assert ctx.evaluate_condition("status == completed") is True
        assert ctx.evaluate_condition("status == failed") is False
        assert ctx.evaluate_condition("code == 0") is True

    def test_inequality(self):
        ctx = WorkflowContext({"status": "completed"})

        assert ctx.evaluate_condition("status != failed") is True
        assert ctx.evaluate_condition("status != completed") is False

    def test_greater_than(self):
        ctx = WorkflowContext({"count": 15})

        assert ctx.evaluate_condition("count > 10") is True
        assert ctx.evaluate_condition("count > 20") is False
        assert ctx.evaluate_condition("count >= 15") is True
        assert ctx.evaluate_condition("count >= 16") is False

    def test_less_than(self):
        ctx = WorkflowContext({"count": 5})

        assert ctx.evaluate_condition("count < 10") is True
        assert ctx.evaluate_condition("count < 3") is False
        assert ctx.evaluate_condition("count <= 5") is True
        assert ctx.evaluate_condition("count <= 4") is False

    def test_contains(self):
        ctx = WorkflowContext({"ports": [80, 443, 8080], "name": "testserver"})

        assert ctx.evaluate_condition("ports contains 80") is True
        assert ctx.evaluate_condition("ports contains 22") is False
        assert ctx.evaluate_condition("name contains test") is True
        assert ctx.evaluate_condition("name contains prod") is False

    def test_nested_path(self):
        ctx = WorkflowContext()
        ctx.set("node_1_result", {"exit_code": 0, "data": {"count": 5}})

        assert ctx.evaluate_condition("node_1_result.exit_code == 0") is True
        assert ctx.evaluate_condition("node_1_result.data.count > 3") is True

    def test_invalid_condition(self):
        ctx = WorkflowContext()
        # Invalid conditions should return False
        assert ctx.evaluate_condition("invalid condition") is False


class TestVariableResolution:
    """Test variable resolution."""

    def test_simple_variable(self):
        ctx = WorkflowContext({"target": "192.168.1.1"})

        result = ctx.resolve_value("${target}")
        assert result == "192.168.1.1"

    def test_nested_variable(self):
        ctx = WorkflowContext()
        ctx.set("node_1_result", {"exit_code": 0, "data": {"ports": [80, 443]}})

        assert ctx.resolve_value("${node_1_result.exit_code}") == 0
        assert ctx.resolve_value("${node_1_result.data.ports}") == [80, 443]

    def test_array_access(self):
        ctx = WorkflowContext()
        ctx.set("node_1_result", {"ports": [80, 443, 8080]})

        assert ctx.resolve_value("${node_1_result.ports[0]}") == 80
        assert ctx.resolve_value("${node_1_result.ports[1]}") == 443

    def test_string_substitution(self):
        ctx = WorkflowContext({"target": "192.168.1.1", "port": 80})

        result = ctx.resolve_value("Scanning ${target} on port ${port}")
        assert result == "Scanning 192.168.1.1 on port 80"

    def test_dict_resolution(self):
        ctx = WorkflowContext({"host": "example.com"})

        result = ctx.resolve_value({"url": "http://${host}", "port": 80})
        assert result == {"url": "http://example.com", "port": 80}

    def test_list_resolution(self):
        ctx = WorkflowContext({"target": "192.168.1.1"})

        result = ctx.resolve_value(["${target}", "192.168.1.2"])
        assert result == ["192.168.1.1", "192.168.1.2"]

    def test_nonexistent_variable(self):
        ctx = WorkflowContext()

        result = ctx.resolve_value("${nonexistent}")
        assert result is None

    def test_partial_substitution(self):
        ctx = WorkflowContext({"host": "example.com"})

        result = ctx.resolve_value("http://${host}/api")
        assert result == "http://example.com/api"


class TestLoopContext:
    """Test loop context management."""

    def test_set_loop_context(self):
        ctx = WorkflowContext()
        ctx.set_loop_context(0, "item1", 3, "loop1")

        assert ctx.get("loop_index") == 0
        assert ctx.get("loop_item") == "item1"
        assert ctx.get("loop_total") == 3
        assert ctx.get("loop_loop1_index") == 0
        assert ctx.get("loop_loop1_item") == "item1"

    def test_clear_loop_context(self):
        ctx = WorkflowContext()
        ctx.set_loop_context(0, "item1", 3)
        ctx.clear_loop_context()

        assert ctx.get("loop_index") is None
        assert ctx.get("loop_item") is None
        assert ctx.get("loop_total") is None

    def test_loop_iteration(self):
        ctx = WorkflowContext()
        items = ["a", "b", "c"]

        for i, item in enumerate(items):
            ctx.set_loop_context(i, item, len(items))
            assert ctx.get("loop_index") == i
            assert ctx.get("loop_item") == item
