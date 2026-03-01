"""Shared test fixtures for hfs-location-client tests."""

from datetime import datetime, timezone

import pytest


@pytest.fixture
def mock_api_url() -> str:
    return "http://localhost:5001/api/v1"


@pytest.fixture
def mock_api_key() -> str:
    return "lr_test_key_abc123"


@pytest.fixture
def sample_building_payload() -> dict:
    """Sample building response matching BuildingDTO."""
    return {
        "id": "b-001",
        "plus_code": "77C2XF2G+4V",
        "plus_code_short": "XF2G+4V Nassau",
        "gers_id": "08b2a-1234",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-77.35, 25.06],
                    [-77.35, 25.061],
                    [-77.349, 25.061],
                    [-77.349, 25.06],
                    [-77.35, 25.06],
                ]
            ],
        },
        "centroid": {"type": "Point", "coordinates": [-77.3495, 25.0605]},
        "area_m2": 150.5,
        "height_m": 8.2,
        "island_id": "i-np",
        "island_name": "New Providence",
        "confidence_tier": "ml-high",
        "source": "overture",
        "source_confidence": 0.85,
        "category": "residential",
        "name": None,
        "street_address": "123 Bay Street",
        "nearest_road_id": "r-001",
        "nearest_road_name": "Bay Street",
        "nearest_road_distance_m": 12.3,
        "cay_id": None,
        "cay_name": None,
        "display_address": "123 Bay Street, New Providence",
        "tags": {},
        "verified_at": None,
        "created_at": "2026-02-15T12:00:00+00:00",
        "updated_at": "2026-02-15T12:00:00+00:00",
        "attribution": "Data sourced from Overture Maps Foundation (ODbL v1.0)",
    }


@pytest.fixture
def sample_road_payload() -> dict:
    """Sample road response matching RoadDTO."""
    return {
        "id": "r-001",
        "gers_id": "08c3b-5678",
        "geometry": {
            "type": "LineString",
            "coordinates": [[-77.35, 25.06], [-77.34, 25.065]],
        },
        "name": "Bay Street",
        "name_alt": None,
        "road_class": "primary",
        "surface": "paved",
        "island_id": "i-np",
        "island_name": "New Providence",
        "length_m": 1234.5,
        "one_way": False,
        "tags": {},
        "source": "overture",
        "created_at": "2026-02-15T12:00:00+00:00",
        "updated_at": "2026-02-15T12:00:00+00:00",
        "attribution": "Data sourced from Overture Maps Foundation (ODbL v1.0)",
    }


@pytest.fixture
def sample_island_payload() -> dict:
    """Sample island response matching IslandDTO."""
    return {
        "id": "i-np",
        "name": "New Providence",
        "name_alt": None,
        "district": "New Providence",
        "centroid": {"type": "Point", "coordinates": [-77.35, 25.06]},
        "area_km2": 207.0,
        "plus_code_prefix": "77C2",
        "population": 274400,
        "inhabited": True,
        "boundary_geojson": None,
        "building_count": 48000,
        "road_count": 5200,
    }


@pytest.fixture
def sample_island_stats_payload() -> dict:
    """Sample island stats response matching IslandStatsDTO."""
    return {
        "island_id": "i-np",
        "island_name": "New Providence",
        "total_buildings": 48000,
        "verified_buildings": 120,
        "satellite_confirmed": 5000,
        "ml_high": 30000,
        "ml_medium": 10000,
        "approximate": 2880,
        "coverage_percent": 85.5,
        "total_roads": 5200,
        "named_roads": 3100,
        "total_road_length_km": 1450.2,
    }


@pytest.fixture
def sample_paginated_buildings(sample_building_payload: dict) -> dict:
    """Sample paginated API response envelope."""
    return {
        "success": True,
        "data": [sample_building_payload],
        "message": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "correlation_id": None,
        "meta": {
            "pagination": {
                "next_cursor": "abc123",
                "has_more": True,
                "total": 48000,
            }
        },
    }
