"""Integration tests against live Location Registry API.

Run with: pytest tests/integration/ -v -m integration
Requires: LR_API_KEY environment variable set.
"""

from __future__ import annotations

import pytest

from hfs_location_client import (
    LocationRegistryClient,
    LocationRegistrySyncClient,
)
from hfs_location_client.exceptions import NotFoundError
from hfs_location_client.models import (
    Building,
    GeocodeResult,
    HealthStatus,
    Island,
    PlusCodeResult,
    ReverseGeocodeResult,
)

# Known coordinates: downtown Nassau, New Providence
NASSAU_LAT = 25.0480
NASSAU_LNG = -77.3554


# ── Async client tests ──────────────────────────────────────────


@pytest.mark.integration
async def test_async_health_check(
    lr_base_url: str, lr_api_key: str,
) -> None:
    async with LocationRegistryClient(
        lr_base_url, lr_api_key,
    ) as client:
        health = await client.health_check()
    assert isinstance(health, HealthStatus)
    assert health.status in ("ready", "healthy")


@pytest.mark.integration
async def test_async_list_islands(
    lr_base_url: str, lr_api_key: str,
) -> None:
    async with LocationRegistryClient(
        lr_base_url, lr_api_key,
    ) as client:
        islands = await client.list_islands()
    assert isinstance(islands, list)
    assert len(islands) == 19
    assert all(isinstance(i, Island) for i in islands)
    names = {i.name for i in islands}
    assert "New Providence" in names


@pytest.mark.integration
async def test_async_reverse_geocode(
    lr_base_url: str, lr_api_key: str,
) -> None:
    async with LocationRegistryClient(
        lr_base_url, lr_api_key,
    ) as client:
        result = await client.reverse_geocode(
            NASSAU_LAT, NASSAU_LNG,
        )
    assert isinstance(result, ReverseGeocodeResult)
    assert result.plus_code is not None


@pytest.mark.integration
async def test_async_geocode(
    lr_base_url: str, lr_api_key: str,
) -> None:
    async with LocationRegistryClient(
        lr_base_url, lr_api_key,
    ) as client:
        results = await client.geocode("Nassau")
    assert isinstance(results, list)
    assert len(results) >= 1
    assert isinstance(results[0], GeocodeResult)


@pytest.mark.integration
async def test_async_encode_plus_code(
    lr_base_url: str, lr_api_key: str,
) -> None:
    async with LocationRegistryClient(
        lr_base_url, lr_api_key,
    ) as client:
        result = await client.encode_plus_code(
            NASSAU_LAT, NASSAU_LNG,
        )
    assert isinstance(result, PlusCodeResult)
    assert result.code is not None
    assert result.is_full is True


@pytest.mark.integration
async def test_async_404_for_nonexistent(
    lr_base_url: str, lr_api_key: str,
) -> None:
    async with LocationRegistryClient(
        lr_base_url, lr_api_key,
    ) as client:
        with pytest.raises(NotFoundError) as exc_info:
            await client.get_building("0000ZZZZ+ZZ")
    assert exc_info.value.status_code == 404


# ── Sync client tests ───────────────────────────────────────────


@pytest.mark.integration
def test_sync_health_check(
    lr_base_url: str, lr_api_key: str,
) -> None:
    with LocationRegistrySyncClient(
        lr_base_url, lr_api_key,
    ) as client:
        health = client.health_check()
    assert isinstance(health, HealthStatus)
    assert health.status in ("ready", "healthy")


@pytest.mark.integration
def test_sync_list_islands(
    lr_base_url: str, lr_api_key: str,
) -> None:
    with LocationRegistrySyncClient(
        lr_base_url, lr_api_key,
    ) as client:
        islands = client.list_islands()
    assert isinstance(islands, list)
    assert len(islands) == 19
    names = {i.name for i in islands}
    assert "New Providence" in names


@pytest.mark.integration
def test_sync_reverse_geocode(
    lr_base_url: str, lr_api_key: str,
) -> None:
    with LocationRegistrySyncClient(
        lr_base_url, lr_api_key,
    ) as client:
        result = client.reverse_geocode(
            NASSAU_LAT, NASSAU_LNG,
        )
    assert isinstance(result, ReverseGeocodeResult)
    assert result.plus_code is not None


@pytest.mark.integration
def test_sync_geocode(
    lr_base_url: str, lr_api_key: str,
) -> None:
    with LocationRegistrySyncClient(
        lr_base_url, lr_api_key,
    ) as client:
        results = client.geocode("Nassau")
    assert isinstance(results, list)
    assert len(results) >= 1


@pytest.mark.integration
def test_sync_404_for_nonexistent(
    lr_base_url: str, lr_api_key: str,
) -> None:
    with LocationRegistrySyncClient(
        lr_base_url, lr_api_key,
    ) as client:
        with pytest.raises(NotFoundError) as exc_info:
            client.get_building("0000ZZZZ+ZZ")
    assert exc_info.value.status_code == 404
