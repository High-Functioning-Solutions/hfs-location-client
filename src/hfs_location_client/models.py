"""Pydantic response models mirroring Location Registry API DTOs.

These models are the typed contract between the client library and its
consumers. Field names and types match the API's Pydantic DTOs exactly.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ── Core Entity Models ──────────────────────────────────────────────


class Building(BaseModel):
    """Mirrors location-registry-api BuildingDTO exactly."""

    id: str
    plus_code: str
    plus_code_short: str | None = None
    gers_id: str | None = None
    geometry: dict[str, Any]  # GeoJSON Polygon
    centroid: dict[str, Any]  # GeoJSON Point
    area_m2: float
    height_m: float | None = None
    island_id: str
    island_name: str
    confidence_tier: str
    source: str
    source_confidence: float | None = None
    category: str | None = None
    name: str | None = None
    street_address: str | None = None
    nearest_road_id: str | None = None
    nearest_road_name: str | None = None
    nearest_road_distance_m: float | None = None
    cay_id: str | None = None
    cay_name: str | None = None
    display_address: str | None = None
    tags: dict[str, Any] = Field(default_factory=dict)
    verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    attribution: str = "Data sourced from Overture Maps Foundation (ODbL v1.0)"


class Road(BaseModel):
    """Mirrors location-registry-api RoadDTO exactly."""

    id: str
    gers_id: str | None = None
    geometry: dict[str, Any]  # GeoJSON LineString
    name: str | None = None
    name_alt: str | None = None
    road_class: str
    surface: str | None = None
    island_id: str | None = None
    island_name: str | None = None
    length_m: float | None = None
    one_way: bool
    tags: dict[str, Any] = Field(default_factory=dict)
    source: str
    created_at: datetime
    updated_at: datetime
    attribution: str = "Data sourced from Overture Maps Foundation (ODbL v1.0)"


class Island(BaseModel):
    """Mirrors location-registry-api IslandDTO exactly."""

    id: str
    name: str
    name_alt: str | None = None
    district: str | None = None
    centroid: dict[str, Any] | None = None  # GeoJSON Point
    area_km2: float | None = None
    plus_code_prefix: str | None = None
    population: int | None = None
    inhabited: bool
    boundary_geojson: dict[str, Any] | None = None  # GeoJSON MultiPolygon
    building_count: int = 0
    road_count: int = 0


class IslandStats(BaseModel):
    """Mirrors location-registry-api IslandStatsDTO — flat fields."""

    island_id: str
    island_name: str
    total_buildings: int
    verified_buildings: int
    satellite_confirmed: int
    ml_high: int
    ml_medium: int
    approximate: int
    coverage_percent: float
    total_roads: int
    named_roads: int
    total_road_length_km: float


# ── Geocoding Models ────────────────────────────────────────────────


class ReverseGeocodeResult(BaseModel):
    """Mirrors location-registry-api ReverseGeocodeResultDTO."""

    plus_code: str
    nearest_building: Building | None = None
    nearest_building_distance_m: float | None = None
    nearest_road: Road | None = None
    nearest_road_distance_m: float | None = None
    island: dict[str, Any] | None = None  # simplified island dict, no boundary


class GeocodeResult(BaseModel):
    """Mirrors location-registry-api GeocodeResultDTO."""

    type: str  # building | road | pluscode
    score: float
    name: str
    plus_code: str | None = None
    centroid: dict[str, Any]  # GeoJSON Point
    island_name: str | None = None
    building: Building | None = None
    road: Road | None = None


# ── Plus Code Models ────────────────────────────────────────────────


class PlusCodeResult(BaseModel):
    """Mirrors location-registry-api PlusCodeDTO."""

    code: str
    is_full: bool
    is_short: bool
    lat: float | None = None
    lng: float | None = None
    south: float | None = None
    north: float | None = None
    west: float | None = None
    east: float | None = None


# ── Pagination ──────────────────────────────────────────────────────


class PaginationMeta(BaseModel):
    """Pagination metadata from API envelope meta.pagination."""

    next_cursor: str | None = None
    has_more: bool
    total: int | None = None


class PaginatedResult(BaseModel, Generic[T]):
    """Wraps paginated API responses.

    The client constructs this from the API's response envelope:
    data -> items, meta.pagination -> pagination fields.
    """

    data: list[T]
    next_cursor: str | None = None
    has_more: bool = False
    total: int | None = None


# ── Health ──────────────────────────────────────────────────────────


class HealthChecks(BaseModel):
    """Individual health check results from /api/v1/health/ready."""

    database: bool
    redis: bool


class HealthStatus(BaseModel):
    """Mirrors /api/v1/health/ready response data field."""

    status: str  # "ready" or "degraded"
    checks: HealthChecks
