"""Pytest configuration and fixtures."""

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_job():
    """Create a mock job for parser testing."""
    job = MagicMock()
    job.project_id = "test-project-id"
    job.parameters = {}
    return job


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    from unittest.mock import AsyncMock
    return AsyncMock()
