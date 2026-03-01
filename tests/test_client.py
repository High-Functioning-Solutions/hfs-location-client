"""Tests for LocationRegistryClient using respx mocking."""

import httpx
import pytest
import respx

from hfs_location_client import LocationRegistryClient
from hfs_location_client.exceptions import (
    CircuitOpenError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
)
from hfs_location_client.models import (
    Building,
    GeocodeResult,
    HealthStatus,
    Island,
    IslandStats,
    PaginatedResult,
    PlusCodeResult,
    ReverseGeocodeResult,
    Road,
)

BASE_URL = "http://lr-test.local/api/v1"
API_KEY = "lr_test_key_abc123"


def _api_envelope(
    data: object, message: str | None = None,
) -> dict:
    """Wrap data in standard API response envelope."""
    return {
        "success": True,
        "data": data,
        "message": message,
        "timestamp": "2026-02-28T12:00:00Z",
        "correlation_id": None,
    }


def _paginated_envelope(
    data: list,
    total: int = 1,
    has_more: bool = False,
    next_cursor: str | None = None,
) -> dict:
    """Wrap data in paginated API response envelope."""
    return {
        "success": True,
        "data": data,
        "message": None,
        "timestamp": "2026-02-28T12:00:00Z",
        "correlation_id": None,
        "meta": {
            "pagination": {
                "next_cursor": next_cursor,
                "has_more": has_more,
                "total": total,
            }
        },
    }


def _error_envelope(code: str, message: str) -> dict:
    """Create an API error response."""
    return {
        "success": False,
        "error": {"code": code, "message": message},
        "timestamp": "2026-02-28T12:00:00Z",
        "correlation_id": None,
    }


@pytest.fixture
def client() -> LocationRegistryClient:
    return LocationRegistryClient(
        base_url=BASE_URL,
        api_key=API_KEY,
        timeout=2.0,
        max_retries=2,
        circuit_breaker_threshold=3,
        circuit_breaker_reset=0.1,
    )


# ── Building tests ──────────────────────────────────────────────


@respx.mock
async def test_get_building(
    client: LocationRegistryClient,
    sample_building_payload: dict,
) -> None:
    respx.get(f"{BASE_URL}/buildings/77C2XF2G%2B4V").mock(
        return_value=httpx.Response(
            200, json=_api_envelope(sample_building_payload),
        )
    )

    building = await client.get_building("77C2XF2G+4V")
    assert isinstance(building, Building)
    assert building.id == "b-001"
    assert building.plus_code == "77C2XF2G+4V"
    assert building.confidence_tier == "ml-high"
    await client.close()


@respx.mock
async def test_search_buildings(
    client: LocationRegistryClient,
    sample_building_payload: dict,
) -> None:
    envelope = _paginated_envelope(
        [sample_building_payload],
        total=48000,
        has_more=True,
        next_cursor="abc",
    )
    respx.get(f"{BASE_URL}/buildings").mock(
        return_value=httpx.Response(200, json=envelope)
    )

    result = await client.search_buildings(
        island_id="i-np", limit=50,
    )
    assert isinstance(result, PaginatedResult)
    assert len(result.data) == 1
    assert isinstance(result.data[0], Building)
    assert result.total == 48000
    assert result.has_more is True
    assert result.next_cursor == "abc"
    await client.close()


# ── Road tests ──────────────────────────────────────────────────


@respx.mock
async def test_get_road(
    client: LocationRegistryClient,
    sample_road_payload: dict,
) -> None:
    respx.get(f"{BASE_URL}/roads/r-001").mock(
        return_value=httpx.Response(
            200, json=_api_envelope(sample_road_payload),
        )
    )

    road = await client.get_road("r-001")
    assert isinstance(road, Road)
    assert road.road_class == "primary"
    assert road.name == "Bay Street"
    await client.close()


@respx.mock
async def test_search_roads(
    client: LocationRegistryClient,
    sample_road_payload: dict,
) -> None:
    envelope = _paginated_envelope(
        [sample_road_payload], total=5200,
    )
    respx.get(f"{BASE_URL}/roads").mock(
        return_value=httpx.Response(200, json=envelope)
    )

    result = await client.search_roads(name="Bay")
    assert isinstance(result, PaginatedResult)
    assert len(result.data) == 1
    assert isinstance(result.data[0], Road)
    await client.close()


# ── Geocoding tests ─────────────────────────────────────────────


@respx.mock
async def test_reverse_geocode(
    client: LocationRegistryClient,
    sample_building_payload: dict,
    sample_road_payload: dict,
) -> None:
    payload = {
        "plus_code": "77C2XF2G+4V",
        "nearest_building": sample_building_payload,
        "nearest_building_distance_m": 5.2,
        "nearest_road": sample_road_payload,
        "nearest_road_distance_m": 12.3,
        "island": {"id": "i-np", "name": "New Providence"},
    }
    respx.get(f"{BASE_URL}/reverse").mock(
        return_value=httpx.Response(
            200, json=_api_envelope(payload),
        )
    )

    result = await client.reverse_geocode(25.06, -77.35)
    assert isinstance(result, ReverseGeocodeResult)
    assert result.plus_code == "77C2XF2G+4V"
    assert result.nearest_building is not None
    await client.close()


@respx.mock
async def test_geocode(
    client: LocationRegistryClient,
    sample_building_payload: dict,
) -> None:
    payload = [
        {
            "type": "building",
            "score": 0.95,
            "name": "123 Bay Street",
            "plus_code": "77C2XF2G+4V",
            "centroid": {
                "type": "Point",
                "coordinates": [-77.35, 25.06],
            },
            "island_name": "New Providence",
            "building": sample_building_payload,
            "road": None,
        }
    ]
    respx.get(f"{BASE_URL}/geocode").mock(
        return_value=httpx.Response(
            200, json=_api_envelope(payload),
        )
    )

    results = await client.geocode("Bay Street")
    assert len(results) == 1
    assert isinstance(results[0], GeocodeResult)
    assert results[0].score == 0.95
    await client.close()


# ── Plus Code tests ─────────────────────────────────────────────


@respx.mock
async def test_encode_plus_code(
    client: LocationRegistryClient,
) -> None:
    payload = {
        "code": "77C2XF2G+4V",
        "is_full": True,
        "is_short": False,
        "lat": 25.06,
        "lng": -77.35,
    }
    respx.get(f"{BASE_URL}/pluscode/encode").mock(
        return_value=httpx.Response(
            200, json=_api_envelope(payload),
        )
    )

    result = await client.encode_plus_code(25.06, -77.35)
    assert isinstance(result, PlusCodeResult)
    assert result.code == "77C2XF2G+4V"
    assert result.is_full is True
    await client.close()


@respx.mock
async def test_decode_plus_code(
    client: LocationRegistryClient,
) -> None:
    payload = {
        "code": "77C2XF2G+4V",
        "is_full": True,
        "is_short": False,
        "lat": 25.06,
        "lng": -77.35,
        "south": 25.059,
        "north": 25.061,
        "west": -77.351,
        "east": -77.349,
    }
    respx.get(f"{BASE_URL}/pluscode/decode").mock(
        return_value=httpx.Response(
            200, json=_api_envelope(payload),
        )
    )

    result = await client.decode_plus_code("77C2XF2G+4V")
    assert isinstance(result, PlusCodeResult)
    assert result.south == 25.059
    await client.close()


@respx.mock
async def test_validate_plus_code(
    client: LocationRegistryClient,
) -> None:
    respx.get(f"{BASE_URL}/pluscode/validate").mock(
        return_value=httpx.Response(
            200,
            json=_api_envelope(
                {"valid": True, "code": "77C2XF2G+4V"},
            ),
        )
    )

    valid = await client.validate_plus_code("77C2XF2G+4V")
    assert valid is True
    await client.close()


# ── Island tests ────────────────────────────────────────────────


@respx.mock
async def test_list_islands(
    client: LocationRegistryClient,
    sample_island_payload: dict,
) -> None:
    respx.get(f"{BASE_URL}/islands").mock(
        return_value=httpx.Response(
            200,
            json=_api_envelope([sample_island_payload]),
        )
    )

    islands = await client.list_islands()
    assert len(islands) == 1
    assert isinstance(islands[0], Island)
    assert islands[0].name == "New Providence"
    await client.close()


@respx.mock
async def test_get_island(
    client: LocationRegistryClient,
    sample_island_payload: dict,
) -> None:
    respx.get(f"{BASE_URL}/islands/i-np").mock(
        return_value=httpx.Response(
            200,
            json=_api_envelope(sample_island_payload),
        )
    )

    island = await client.get_island("i-np")
    assert isinstance(island, Island)
    assert island.inhabited is True
    await client.close()


@respx.mock
async def test_get_island_stats(
    client: LocationRegistryClient,
    sample_island_stats_payload: dict,
) -> None:
    respx.get(f"{BASE_URL}/islands/i-np/stats").mock(
        return_value=httpx.Response(
            200,
            json=_api_envelope(
                sample_island_stats_payload,
            ),
        )
    )

    stats = await client.get_island_stats("i-np")
    assert isinstance(stats, IslandStats)
    assert stats.total_buildings == 48000
    assert stats.coverage_percent == 85.5
    await client.close()


# ── Health tests ────────────────────────────────────────────────


@respx.mock
async def test_health_check(
    client: LocationRegistryClient,
) -> None:
    payload = {
        "status": "ready",
        "checks": {"database": True, "redis": True},
    }
    respx.get(f"{BASE_URL}/health/ready").mock(
        return_value=httpx.Response(
            200, json=_api_envelope(payload),
        )
    )

    health = await client.health_check()
    assert isinstance(health, HealthStatus)
    assert health.status == "ready"
    assert health.checks.database is True
    await client.close()


# ── Error handling tests ────────────────────────────────────────


@respx.mock
async def test_404_raises_not_found(
    client: LocationRegistryClient,
) -> None:
    respx.get(f"{BASE_URL}/buildings/INVALID").mock(
        return_value=httpx.Response(
            404,
            json=_error_envelope(
                "NOT_FOUND", "Building not found",
            ),
        )
    )

    with pytest.raises(NotFoundError) as exc_info:
        await client.get_building("INVALID")
    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "NOT_FOUND"
    await client.close()


@respx.mock
async def test_400_raises_validation_error(
    client: LocationRegistryClient,
) -> None:
    respx.get(f"{BASE_URL}/pluscode/validate").mock(
        return_value=httpx.Response(
            400,
            json=_error_envelope(
                "VALIDATION_ERROR", "Invalid code",
            ),
        )
    )

    with pytest.raises(ValidationError) as exc_info:
        await client.validate_plus_code("bad")
    assert exc_info.value.status_code == 400
    await client.close()


@respx.mock
async def test_429_raises_rate_limit(
    client: LocationRegistryClient,
) -> None:
    route = respx.get(f"{BASE_URL}/buildings")
    route.mock(
        return_value=httpx.Response(
            429,
            headers={"Retry-After": "0.01"},
            json=_error_envelope(
                "RATE_LIMITED", "Too many requests",
            ),
        )
    )

    with pytest.raises(RateLimitError) as exc_info:
        await client.search_buildings()
    assert exc_info.value.retry_after == 0.01
    # 429 is retried — call count equals max_retries
    assert route.call_count == 2
    await client.close()


@respx.mock
async def test_429_retries_then_succeeds(
    client: LocationRegistryClient,
    sample_building_payload: dict,
) -> None:
    route = respx.get(
        f"{BASE_URL}/buildings/77C2XF2G%2B4V",
    )
    route.side_effect = [
        httpx.Response(
            429,
            headers={"Retry-After": "0.01"},
            json=_error_envelope(
                "RATE_LIMITED", "Too many requests",
            ),
        ),
        httpx.Response(
            200,
            json=_api_envelope(sample_building_payload),
        ),
    ]

    building = await client.get_building("77C2XF2G+4V")
    assert isinstance(building, Building)
    assert route.call_count == 2
    await client.close()


# ── Retry tests ─────────────────────────────────────────────────


@respx.mock
async def test_5xx_triggers_retry(
    client: LocationRegistryClient,
    sample_building_payload: dict,
) -> None:
    route = respx.get(
        f"{BASE_URL}/buildings/77C2XF2G%2B4V",
    )
    route.side_effect = [
        httpx.Response(
            503,
            json=_error_envelope("UNAVAILABLE", "Down"),
        ),
        httpx.Response(
            200,
            json=_api_envelope(sample_building_payload),
        ),
    ]

    building = await client.get_building("77C2XF2G+4V")
    assert isinstance(building, Building)
    assert route.call_count == 2
    await client.close()


@respx.mock
async def test_5xx_exhausts_retries(
    client: LocationRegistryClient,
) -> None:
    respx.get(f"{BASE_URL}/buildings/77C2XF2G%2B4V").mock(
        return_value=httpx.Response(
            503,
            json=_error_envelope("UNAVAILABLE", "Down"),
        )
    )

    with pytest.raises(ServiceUnavailableError):
        await client.get_building("77C2XF2G+4V")
    await client.close()


# ── Circuit breaker tests ───────────────────────────────────────


@respx.mock
async def test_circuit_breaker_opens_after_failures(
    client: LocationRegistryClient,
) -> None:
    respx.get(f"{BASE_URL}/health/ready").mock(
        return_value=httpx.Response(
            503,
            json=_error_envelope("UNAVAILABLE", "Down"),
        )
    )

    for _ in range(3):
        with pytest.raises(ServiceUnavailableError):
            await client.health_check()

    with pytest.raises(CircuitOpenError):
        await client.health_check()
    await client.close()


# ── Client lifecycle tests ──────────────────────────────────────


@respx.mock
async def test_close_cleans_up(
    client: LocationRegistryClient,
) -> None:
    await client.close()
    assert client._http.is_closed


@respx.mock
async def test_context_manager() -> None:
    async with LocationRegistryClient(
        BASE_URL, API_KEY,
    ) as client:
        assert not client._http.is_closed
    assert client._http.is_closed


@respx.mock
async def test_api_key_header(
    client: LocationRegistryClient,
    sample_island_payload: dict,
) -> None:
    route = respx.get(f"{BASE_URL}/islands").mock(
        return_value=httpx.Response(
            200,
            json=_api_envelope([sample_island_payload]),
        )
    )

    await client.list_islands()
    request_headers = route.calls[0].request.headers
    assert request_headers["X-Api-Key"] == API_KEY
    await client.close()
