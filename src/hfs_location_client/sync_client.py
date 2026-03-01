"""Synchronous client for Location Registry API.

Provides the same typed interface as LocationRegistryClient but using
httpx.Client (blocking) for Flask/sync consumers like Clinic Connect.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
)

from hfs_location_client._shared import (
    NON_RETRYABLE_CODES,
    ServerError,
    build_params,
    map_error,
    parse_paginated,
    rate_limit_aware_wait,
)
from hfs_location_client._sync_circuit_breaker import SyncCircuitBreaker
from hfs_location_client.exceptions import RateLimitError
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

logger = logging.getLogger(__name__)


class LocationRegistrySyncClient:
    """Synchronous client for Location Registry API.

    Usage::

        client = LocationRegistrySyncClient(
            base_url="http://localhost:5001/api/v1",
            api_key="lr_live_key_...",
        )
        building = client.get_building("77C2XF2G+4V")
        client.close()

    All public methods return typed Pydantic models.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 5.0,
        max_retries: int = 3,
        circuit_breaker_threshold: int = 3,
        circuit_breaker_reset: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._http = httpx.Client(
            base_url=self._base_url,
            headers={"X-Api-Key": api_key},
            timeout=timeout,
        )
        self._circuit = SyncCircuitBreaker(
            failure_threshold=circuit_breaker_threshold,
            recovery_timeout=circuit_breaker_reset,
        )
        self._max_retries = max_retries

    # ── Buildings ────────────────────────────────────────────────────

    def get_building(self, plus_code: str) -> Building:
        """Get a building by its Plus Code."""
        path = f"/buildings/{quote(plus_code, safe='')}"
        data = self._request("GET", path)
        return Building.model_validate(data)

    def search_buildings(
        self,
        *,
        island_id: str | None = None,
        confidence_tier: str | None = None,
        lat: float | None = None,
        lng: float | None = None,
        radius_m: float | None = None,
        bbox: str | None = None,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> PaginatedResult[Building]:
        """Search buildings with spatial and attribute filters."""
        params = build_params(
            island_id=island_id,
            confidence_tier=confidence_tier,
            lat=lat,
            lng=lng,
            radius_m=radius_m,
            bbox=bbox,
            cursor=cursor,
            limit=limit,
        )
        envelope = self._request(
            "GET", "/buildings",
            params=params, parse_envelope=False,
        )
        return parse_paginated(envelope, Building)

    # ── Roads ────────────────────────────────────────────────────────

    def get_road(self, road_id: str) -> Road:
        """Get a road by its UUID."""
        data = self._request("GET", f"/roads/{road_id}")
        return Road.model_validate(data)

    def search_roads(
        self,
        *,
        island_id: str | None = None,
        name: str | None = None,
        road_class: str | None = None,
        lat: float | None = None,
        lng: float | None = None,
        radius_m: float | None = None,
        bbox: str | None = None,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> PaginatedResult[Road]:
        """Search roads with spatial and attribute filters."""
        params = build_params(
            island_id=island_id,
            name=name,
            road_class=road_class,
            lat=lat,
            lng=lng,
            radius_m=radius_m,
            bbox=bbox,
            cursor=cursor,
            limit=limit,
        )
        envelope = self._request(
            "GET", "/roads",
            params=params, parse_envelope=False,
        )
        return parse_paginated(envelope, Road)

    # ── Geocoding ────────────────────────────────────────────────────

    def reverse_geocode(
        self, lat: float, lng: float,
    ) -> ReverseGeocodeResult:
        """Reverse geocode coordinates to nearest location."""
        data = self._request(
            "GET", "/reverse", params={"lat": lat, "lng": lng},
        )
        return ReverseGeocodeResult.model_validate(data)

    def geocode(self, query: str) -> list[GeocodeResult]:
        """Text geocode — search locations by query string."""
        data = self._request(
            "GET", "/geocode", params={"q": query},
        )
        if isinstance(data, list):
            return [GeocodeResult.model_validate(i) for i in data]
        return [GeocodeResult.model_validate(data)]

    # ── Plus Code ────────────────────────────────────────────────────

    def encode_plus_code(
        self, lat: float, lng: float,
    ) -> PlusCodeResult:
        """Encode latitude/longitude to a Plus Code."""
        params = {"lat": lat, "lng": lng}
        data = self._request(
            "GET", "/pluscode/encode", params=params,
        )
        return PlusCodeResult.model_validate(data)

    def decode_plus_code(self, code: str) -> PlusCodeResult:
        """Decode a Plus Code to coordinates and bounds."""
        data = self._request(
            "GET", "/pluscode/decode", params={"code": code},
        )
        return PlusCodeResult.model_validate(data)

    def validate_plus_code(self, code: str) -> bool:
        """Check if a Plus Code string is valid."""
        data = self._request(
            "GET", "/pluscode/validate", params={"code": code},
        )
        if isinstance(data, dict):
            return bool(data.get("valid", False))
        return bool(data)

    # ── Islands ──────────────────────────────────────────────────────

    def list_islands(self) -> list[Island]:
        """List all island groups."""
        data = self._request("GET", "/islands")
        if isinstance(data, list):
            return [Island.model_validate(i) for i in data]
        return [Island.model_validate(data)]

    def get_island(self, id_or_name: str) -> Island:
        """Get an island by ID or name."""
        path = f"/islands/{quote(id_or_name, safe='')}"
        data = self._request("GET", path)
        return Island.model_validate(data)

    def get_island_stats(
        self, id_or_name: str,
    ) -> IslandStats:
        """Get coverage statistics for a specific island."""
        path = f"/islands/{quote(id_or_name, safe='')}/stats"
        data = self._request("GET", path)
        return IslandStats.model_validate(data)

    # ── Health ───────────────────────────────────────────────────────

    def health_check(self) -> HealthStatus:
        """Check API readiness (database + redis)."""
        data = self._request("GET", "/health/ready")
        return HealthStatus.model_validate(data)

    # ── Lifecycle ────────────────────────────────────────────────────

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._http.close()

    def __enter__(self) -> LocationRegistrySyncClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # ── Internal ─────────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        parse_envelope: bool = True,
    ) -> Any:
        """Core request method with circuit breaker + retry."""

        def _do_request() -> Any:
            response = self._http.request(
                method, path, params=params,
            )

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                raise RateLimitError(
                    "Rate limit exceeded",
                    code="RATE_LIMITED",
                    status_code=429,
                    retry_after=(
                        float(retry_after) if retry_after else None
                    ),
                )

            if response.status_code >= 400:
                error = map_error(
                    response.status_code, response.json(),
                )
                if response.status_code in NON_RETRYABLE_CODES:
                    raise error
                raise ServerError(error)

            body = response.json()

            if (
                parse_envelope
                and isinstance(body, dict)
                and "data" in body
            ):
                return body["data"]
            if not parse_envelope:
                return body
            return body

        try:
            retrying = retry(
                stop=stop_after_attempt(self._max_retries),
                wait=rate_limit_aware_wait,
                retry=retry_if_exception_type(
                    (
                        ServerError,
                        httpx.TransportError,
                        RateLimitError,
                    ),
                ),
                reraise=True,
            )
            return self._circuit.call(retrying(_do_request))
        except ServerError as exc:
            raise exc.original from exc
