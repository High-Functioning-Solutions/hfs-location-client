"""Fixtures for integration tests against live LR API."""

from __future__ import annotations

import os

import pytest

LR_BASE_URL = os.environ.get(
    "LR_BASE_URL", "http://localhost:5001/api/v1",
)
LR_API_KEY = os.environ.get("LR_API_KEY", "")


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item],
) -> None:
    """Auto-mark all tests in integration/ as integration."""
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


@pytest.fixture
def lr_base_url() -> str:
    if not LR_API_KEY:
        pytest.skip("LR_API_KEY not set")
    return LR_BASE_URL


@pytest.fixture
def lr_api_key() -> str:
    if not LR_API_KEY:
        pytest.skip("LR_API_KEY not set")
    return LR_API_KEY
