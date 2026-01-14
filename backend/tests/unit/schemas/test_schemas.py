"""Tests for Pydantic schemas."""

import pytest
from datetime import datetime
from uuid import uuid4

from pydantic import ValidationError

from app.schemas.tool import (
    ToolDefinition,
    ToolParameter,
    ToolOutput,
    ParameterType,
    ToolCategory,
)
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.schemas.job import JobCreate, JobStatus


class TestToolSchemas:
    """Test tool-related schemas."""

    def test_tool_parameter_valid(self):
        """Test creating a valid tool parameter."""
        param = ToolParameter(
            name="target",
            label="Target",
            type=ParameterType.TARGET,
            description="Target IP or hostname",
            required=True,
        )
        assert param.name == "target"
        assert param.type == ParameterType.TARGET
        assert param.required is True

    def test_tool_parameter_with_options(self):
        """Test creating a select parameter with options."""
        param = ToolParameter(
            name="scan_type",
            label="Scan Type",
            type=ParameterType.SELECT,
            options=[
                {"value": "quick", "label": "Quick Scan"},
                {"value": "full", "label": "Full Scan"},
            ],
        )
        assert param.type == ParameterType.SELECT
        assert len(param.options) == 2

    def test_tool_parameter_default_values(self):
        """Test default values for tool parameter."""
        param = ToolParameter(
            name="port",
            label="Port",
            type=ParameterType.PORT,
        )
        assert param.required is False
        assert param.default is None
        assert param.advanced is False

    def test_tool_definition_valid(self):
        """Test creating a valid tool definition."""
        tool = ToolDefinition(
            slug="nmap-test",
            name="Nmap Test",
            description="Network scanner",
            category=ToolCategory.RECONNAISSANCE,
            docker_image="nmap:latest",
            command_template="nmap {target}",
            output=ToolOutput(format="xml", parser="nmap_parser"),
            parameters=[
                ToolParameter(
                    name="target",
                    label="Target",
                    type=ParameterType.TARGET,
                    required=True,
                )
            ],
        )
        assert tool.slug == "nmap-test"
        assert len(tool.parameters) == 1

    def test_tool_definition_invalid_slug(self):
        """Test that invalid slugs are rejected."""
        with pytest.raises(ValidationError):
            ToolDefinition(
                slug="Invalid Slug With Spaces",
                name="Test",
                description="Test",
                category=ToolCategory.RECONNAISSANCE,
                docker_image="test:latest",
                command_template="test",
                output=ToolOutput(format="text"),
            )

    def test_tool_output_schema(self):
        """Test tool output schema."""
        output = ToolOutput(
            format="json",
            parser="nuclei_parser",
            creates_assets=True,
            creates_vulnerabilities=True,
        )
        assert output.format == "json"
        assert output.creates_assets is True


class TestProjectSchemas:
    """Test project-related schemas."""

    def test_project_create_valid(self):
        """Test creating a valid project."""
        project = ProjectCreate(
            name="Test Project",
            description="A test project",
        )
        assert project.name == "Test Project"

    def test_project_create_minimal(self):
        """Test creating a project with minimal fields."""
        project = ProjectCreate(name="Minimal Project")
        assert project.name == "Minimal Project"
        assert project.description is None

    def test_project_update_partial(self):
        """Test partial project update."""
        update = ProjectUpdate(name="Updated Name")
        assert update.name == "Updated Name"
        assert update.description is None


class TestJobSchemas:
    """Test job-related schemas."""

    def test_job_create_valid(self):
        """Test creating a valid job."""
        job = JobCreate(
            project_id=uuid4(),
            tool_name="nmap",
            parameters={"target": "192.168.1.1"},
        )
        assert job.tool_name == "nmap"
        assert job.parameters["target"] == "192.168.1.1"

    def test_job_status_enum(self):
        """Test job status enum values."""
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.CANCELLED.value == "cancelled"


class TestParameterTypes:
    """Test parameter type enum."""

    def test_all_parameter_types(self):
        """Test all parameter types are defined."""
        types = list(ParameterType)
        assert ParameterType.STRING in types
        assert ParameterType.INTEGER in types
        assert ParameterType.BOOLEAN in types
        assert ParameterType.SELECT in types
        assert ParameterType.TARGET in types
        assert ParameterType.PORT in types
        assert ParameterType.WORDLIST in types
        assert ParameterType.TEXTAREA in types
        assert ParameterType.SECRET in types


class TestToolCategories:
    """Test tool category enum."""

    def test_all_categories(self):
        """Test all tool categories are defined."""
        categories = list(ToolCategory)
        assert ToolCategory.RECONNAISSANCE in categories
        assert ToolCategory.VULNERABILITY_SCANNING in categories
        assert ToolCategory.WEB_APPLICATION in categories
        assert ToolCategory.PASSWORD_ATTACKS in categories
        assert ToolCategory.EXPLOITATION in categories
        assert ToolCategory.FORENSICS in categories
