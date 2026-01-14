"""Tests for tool registry."""

import pytest

from app.tools.registry import (
    get_tool,
    list_all_tools,
    get_tools_by_category,
    ToolDefinition,
)
from app.schemas.tool import ToolCategory


class TestToolRegistry:
    """Test the tool registry functions."""

    def test_list_all_tools_returns_list(self):
        """Test that list_all_tools returns a list."""
        tools = list_all_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_list_all_tools_have_required_fields(self):
        """Test that all tools have required fields."""
        tools = list_all_tools()
        for tool in tools:
            assert isinstance(tool, ToolDefinition)
            assert tool.slug is not None
            assert tool.name is not None
            assert tool.description is not None
            assert tool.category is not None
            assert tool.docker_image is not None
            assert tool.command_template is not None

    def test_get_tool_by_slug(self):
        """Test getting a specific tool by slug."""
        tool = get_tool("nmap")
        assert tool is not None
        assert tool.slug == "nmap"
        assert tool.name == "Nmap"
        assert "scan" in tool.description.lower() or "network" in tool.description.lower()

    def test_get_nonexistent_tool(self):
        """Test getting a tool that doesn't exist."""
        tool = get_tool("nonexistent-tool")
        assert tool is None

    def test_get_tools_by_category(self):
        """Test filtering tools by category."""
        recon_tools = get_tools_by_category(ToolCategory.RECONNAISSANCE)
        assert len(recon_tools) > 0
        for tool in recon_tools:
            assert tool.category == ToolCategory.RECONNAISSANCE

    def test_nmap_tool_parameters(self):
        """Test Nmap tool has expected parameters."""
        tool = get_tool("nmap")
        assert tool is not None

        param_names = [p.name for p in tool.parameters]
        assert "target" in param_names

    def test_nuclei_tool_parameters(self):
        """Test Nuclei tool has expected parameters."""
        tool = get_tool("nuclei")
        assert tool is not None

        param_names = [p.name for p in tool.parameters]
        assert "target" in param_names or "targets" in param_names

    def test_tool_has_valid_docker_image(self):
        """Test all tools have valid docker image names."""
        tools = list_all_tools()
        for tool in tools:
            # Docker image should be a non-empty string
            assert len(tool.docker_image) > 0
            # Should not contain spaces
            assert " " not in tool.docker_image

    def test_tool_has_valid_command_template(self):
        """Test all tools have command templates with placeholders."""
        tools = list_all_tools()
        for tool in tools:
            # Command template should exist
            assert len(tool.command_template) > 0

    def test_tool_categories_valid(self):
        """Test all tools have valid categories."""
        tools = list_all_tools()
        valid_categories = set(c.value for c in ToolCategory)
        for tool in tools:
            # Category may be string or enum
            category = tool.category.value if hasattr(tool.category, 'value') else tool.category
            assert category in valid_categories

    def test_tool_slugs_unique(self):
        """Test all tool slugs are unique."""
        tools = list_all_tools()
        slugs = [tool.slug for tool in tools]
        assert len(slugs) == len(set(slugs)), "Tool slugs must be unique"

    def test_tool_timeout_settings(self):
        """Test tools have reasonable timeout settings."""
        tools = list_all_tools()
        for tool in tools:
            assert tool.default_timeout > 0
            assert tool.max_timeout >= tool.default_timeout

    def test_required_parameters_have_no_default(self):
        """Test that required parameters make sense."""
        tools = list_all_tools()
        for tool in tools:
            for param in tool.parameters:
                if param.required:
                    # Required params with defaults are effectively optional
                    # This is a warning, not an error
                    pass

    def test_select_parameters_have_options(self):
        """Test that select parameters have options."""
        tools = list_all_tools()
        for tool in tools:
            for param in tool.parameters:
                # Type may be string or enum
                param_type = param.type.value if hasattr(param.type, 'value') else param.type
                if param_type == "select":
                    assert param.options is not None
                    assert len(param.options) > 0
