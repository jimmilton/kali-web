"""Workflow context management for variable substitution and state passing."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class WorkflowContext:
    """
    Manages workflow execution context.

    The context stores:
    - Node results: node_{node_id}_result
    - Loop variables: loop_index, loop_item, loop_total
    - Input parameters from workflow run
    - Custom variables set by nodes
    """

    def __init__(self, input_params: dict[str, Any] | None = None):
        """Initialize workflow context with optional input parameters."""
        self._data: dict[str, Any] = {}
        if input_params:
            self._data.update(input_params)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from context."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in context."""
        self._data[key] = value

    def update(self, data: dict[str, Any]) -> None:
        """Update context with multiple values."""
        self._data.update(data)

    def get_all(self) -> dict[str, Any]:
        """Get all context data."""
        return self._data.copy()

    def set_node_result(self, node_id: str, result: Any) -> None:
        """Store a node's result in context."""
        self.set(f"node_{node_id}_result", result)

    def get_node_result(self, node_id: str) -> Any:
        """Get a node's result from context."""
        return self.get(f"node_{node_id}_result")

    def set_loop_context(
        self, index: int, item: Any, total: int, loop_id: str | None = None
    ) -> None:
        """Set loop iteration context variables."""
        self.set("loop_index", index)
        self.set("loop_item", item)
        self.set("loop_total", total)
        if loop_id:
            self.set(f"loop_{loop_id}_index", index)
            self.set(f"loop_{loop_id}_item", item)

    def clear_loop_context(self) -> None:
        """Clear loop-specific context variables."""
        for key in ["loop_index", "loop_item", "loop_total"]:
            if key in self._data:
                del self._data[key]

    def resolve_value(self, value: Any) -> Any:
        """
        Resolve variable references in a value.

        Supports:
        - Simple references: ${node_1_result}
        - Nested references: ${node_1_result.exit_code}
        - Array access: ${node_1_result.ports[0]}
        """
        if isinstance(value, str):
            return self._resolve_string(value)
        elif isinstance(value, dict):
            return {k: self.resolve_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.resolve_value(v) for v in value]
        return value

    def _resolve_string(self, value: str) -> Any:
        """Resolve variable references in a string."""
        # Pattern to match ${variable} or ${variable.path}
        pattern = r"\$\{([^}]+)\}"

        # If the entire string is a single variable, return the actual value
        full_match = re.fullmatch(pattern, value)
        if full_match:
            return self._resolve_path(full_match.group(1))

        # Otherwise, do string substitution
        def replace_var(match):
            path = match.group(1)
            resolved = self._resolve_path(path)
            return str(resolved) if resolved is not None else ""

        return re.sub(pattern, replace_var, value)

    def _resolve_path(self, path: str) -> Any:
        """
        Resolve a dot-separated path to a value.

        Examples:
        - "node_1_result" -> context["node_1_result"]
        - "node_1_result.exit_code" -> context["node_1_result"]["exit_code"]
        - "node_1_result.ports[0]" -> context["node_1_result"]["ports"][0]
        """
        # Handle array access notation
        array_pattern = r"(\w+)\[(\d+)\]"

        parts = path.split(".")
        value = self._data

        for part in parts:
            if value is None:
                return None

            # Check for array access
            array_match = re.match(array_pattern, part)
            if array_match:
                key = array_match.group(1)
                index = int(array_match.group(2))
                if isinstance(value, dict) and key in value:
                    value = value[key]
                    if isinstance(value, list) and len(value) > index:
                        value = value[index]
                    else:
                        return None
                else:
                    return None
            else:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return None

        return value

    def evaluate_condition(self, condition: str) -> bool:
        """
        Evaluate a simple key-value condition.

        Supports operators: ==, !=, >, <, >=, <=, contains

        Examples:
        - "status == completed"
        - "node_1_result.exit_code == 0"
        - "port_count > 10"
        - "ports contains 80"
        """
        condition = condition.strip()

        # Parse the condition
        operators = ["==", "!=", ">=", "<=", ">", "<", " contains "]

        for op in operators:
            if op in condition:
                parts = condition.split(op, 1)
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()

                    # Resolve the left side (variable reference)
                    left_value = self._resolve_path(left)

                    # Resolve the right side (could be literal or variable)
                    if right.startswith("${"):
                        right_value = self.resolve_value(right)
                    else:
                        right_value = self._parse_literal(right)

                    return self._compare(left_value, op.strip(), right_value)

        logger.warning(f"Could not parse condition: {condition}")
        return False

    def _parse_literal(self, value: str) -> Any:
        """Parse a literal value from string."""
        # Remove quotes if present
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]

        # Try to parse as number
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # Boolean literals
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
        if value.lower() == "null" or value.lower() == "none":
            return None

        # Return as string
        return value

    def _compare(self, left: Any, op: str, right: Any) -> bool:
        """Compare two values with an operator."""
        try:
            if op == "==":
                return left == right
            elif op == "!=":
                return left != right
            elif op == ">":
                return left > right
            elif op == "<":
                return left < right
            elif op == ">=":
                return left >= right
            elif op == "<=":
                return left <= right
            elif op == "contains":
                if isinstance(left, (list, str)):
                    return right in left
                return False
        except (TypeError, ValueError) as e:
            logger.warning(f"Comparison error: {e}")
            return False

        return False

    def __repr__(self) -> str:
        return f"<WorkflowContext keys={list(self._data.keys())}>"
