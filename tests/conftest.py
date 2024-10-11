"""Configuration for all tests."""

from pathlib import Path

import pytest


@pytest.fixture
def resources_path() -> Path:
    """Fixture for create a path to test resources."""
    return Path(__file__).parent / "resources"
