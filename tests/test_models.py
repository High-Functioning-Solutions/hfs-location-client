"""Tests for Pydantic response models — verify parsing from API payloads."""

from hfs_location_client.models import (
    Building,
    GeocodeResult,
    HealthChecks,
    HealthStatus,
    Island,
    IslandStats,
    PaginatedResult,
    PlusCodeResult,
    ReverseGeocodeResult,
    Road,
)


def test_building_from_payload(sample_building_payload: dict) -> None:
    building = Building.model_validate(sample_building_payload)
    assert building.id == "b-001"
    assert building.plus_code == "77C2XF2G+4V"
    assert building.confidence_tier == "ml-high"
    assert building.area_m2 == 150.5
    assert building.island_name == "New Providence"
    assert building.nearest_road_name == "Bay Street"
    assert building.display_address == "123 Bay Street, New Providence"
    assert building.tags == {}


def test_road_from_payload(sample_road_payload: dict) -> None:
    road = Road.model_validate(sample_road_payload)
    assert road.id == "r-001"
    assert road.road_class == "primary"
    assert road.one_way is False
    assert road.length_m == 1234.5
    assert road.name == "Bay Street"


def test_island_from_payload(sample_island_payload: dict) -> None:
    island = Island.model_validate(sample_island_payload)
    assert island.id == "i-np"
    assert island.name == "New Providence"
    assert island.inhabited is True
    assert island.building_count == 48000
    assert island.population == 274400
    assert island.plus_code_prefix == "77C2"


def test_island_stats_from_payload(sample_island_stats_payload: dict) -> None:
    stats = IslandStats.model_validate(sample_island_stats_payload)
    assert stats.island_id == "i-np"
    assert stats.total_buildings == 48000
    assert stats.verified_buildings == 120
    assert stats.satellite_confirmed == 5000
    assert stats.coverage_percent == 85.5
    assert stats.named_roads == 3100
    assert stats.total_road_length_km == 1450.2


def test_reverse_geocode_result(sample_building_payload: dict, sample_road_payload: dict) -> None:
    payload = {
        "plus_code": "77C2XF2G+4V",
        "nearest_building": sample_building_payload,
        "nearest_building_distance_m": 5.2,
        "nearest_road": sample_road_payload,
        "nearest_road_distance_m": 12.3,
        "island": {"id": "i-np", "name": "New Providence"},
    }
    result = ReverseGeocodeResult.model_validate(payload)
    assert result.plus_code == "77C2XF2G+4V"
    assert result.nearest_building is not None
    assert result.nearest_building.id == "b-001"
    assert result.nearest_building_distance_m == 5.2
    assert result.nearest_road is not None
    assert result.island == {"id": "i-np", "name": "New Providence"}


def test_geocode_result(sample_building_payload: dict) -> None:
    payload = {
        "type": "building",
        "score": 0.95,
        "name": "123 Bay Street",
        "plus_code": "77C2XF2G+4V",
        "centroid": {"type": "Point", "coordinates": [-77.3495, 25.0605]},
        "island_name": "New Providence",
        "building": sample_building_payload,
        "road": None,
    }
    result = GeocodeResult.model_validate(payload)
    assert result.type == "building"
    assert result.score == 0.95
    assert result.building is not None
    assert result.centroid["type"] == "Point"


def test_plus_code_result() -> None:
    payload = {
        "code": "77C2XF2G+4V",
        "is_full": True,
        "is_short": False,
        "lat": 25.0605,
        "lng": -77.3495,
        "south": 25.06,
        "north": 25.061,
        "west": -77.35,
        "east": -77.349,
    }
    result = PlusCodeResult.model_validate(payload)
    assert result.code == "77C2XF2G+4V"
    assert result.is_full is True
    assert result.south == 25.06
    assert result.north == 25.061


def test_paginated_result(sample_building_payload: dict) -> None:
    result = PaginatedResult[Building].model_validate({
        "data": [sample_building_payload],
        "next_cursor": "abc123",
        "has_more": True,
        "total": 48000,
    })
    assert len(result.data) == 1
    assert isinstance(result.data[0], Building)
    assert result.next_cursor == "abc123"
    assert result.has_more is True
    assert result.total == 48000


def test_health_status() -> None:
    payload = {
        "status": "ready",
        "checks": {"database": True, "redis": True},
    }
    health = HealthStatus.model_validate(payload)
    assert health.status == "ready"
    assert health.checks.database is True
    assert health.checks.redis is True
