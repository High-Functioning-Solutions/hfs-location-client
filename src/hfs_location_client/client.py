"""Async client for Location Registry API.

Provides typed methods for all read endpoints with automatic retry
(tenacity) and circuit breaker protection.
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
    wait_exponential_jitter,
)

from hfs_location_client._circuit_breaker import CircuitBreaker
from hfs_location_client.exceptions import (
    AuthError,
    LocationRegistryError,
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

logger = logging.getLogger(__name__)

# 4xx errors should NOT be retried
_NON_RETRYABLE_CODES = {400, 401, 403, 404, 422}


class _ServerError(Exception):
    """Internal wrapper for 5xx errors that should trigger retry."""

    def __init__(self, original: LocationRegistryError) -> None:
        self.original = original
        super().__init__(str(original))


class LocationRegistryClient:
    """Async client for Location Registry API.

    Usage::

        client = LocationRegistryClient(
            base_url="http://localhost:5001/api/v1",
            api_key="lr_live_key_...",
        )
        building = await client.get_building("77C2XF2G+4V")
        await client.close()

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
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"X-Api-Key": api_key},
            timeout=timeout,
        )
        self._circuit = CircuitBreaker(
            failure_threshold=circuit_breaker_threshold,
            recovery_timeout=circuit_breaker_reset,
        )
        self._max_retries = max_retries

    # ── Buildings ────────────────────────────────────────────────────

    async def get_building(self, plus_code: str) -> Building:
        """Get a building by its Plus Code."""
        data = await self._request("GET", f"/buildings/{quote(plus_code, safe='')}")
        return Building.model_validate(data)

    async def search_buildings(
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
        params = _build_params(
            island_id=island_id,
            confidence_tier=confidence_tier,
            lat=lat,
            lng=lng,
            radius_m=radius_m,
            bbox=bbox,
            cursor=cursor,
            limit=limit,
        )
        envelope = await self._request(
            "GET", "/buildings", params=params, parse_envelope=False,
        )
        return _parse_paginated(envelope, Building)

    # ── Roads ────────────────────────────────────────────────────────

    async def get_road(self, road_id: str) -> Road:
        """Get a road by its UUID."""
        data = await self._request("GET", f"/roads/{road_id}")
        return Road.model_validate(data)

    async def search_roads(
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
        params = _build_params(
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
        envelope = await self._request(
            "GET", "/roads", params=params, parse_envelope=False,
        )
        return _parse_paginated(envelope, Road)

    # ── Geocoding ────────────────────────────────────────────────────

    async def reverse_geocode(self, lat: float, lng: float) -> ReverseGeocodeResult:
        """Reverse geocode coordinates to nearest location."""
        data = await self._request("GET", "/reverse", params={"lat": lat, "lng": lng})
        return ReverseGeocodeResult.model_validate(data)

    async def geocode(self, query: str) -> list[GeocodeResult]:
        """Text geocode — search locations by query string."""
        data = await self._request("GET", "/geocode", params={"q": query})
        if isinstance(data, list):
            return [GeocodeResult.model_validate(item) for item in data]
        return [GeocodeResult.model_validate(data)]

    # ── Plus Code ────────────────────────────────────────────────────

    async def encode_plus_code(self, lat: float, lng: float) -> PlusCodeResult:
        """Encode latitude/longitude to a Plus Code."""
        params = {"lat": lat, "lng": lng}
        data = await self._request("GET", "/pluscode/encode", params=params)
        return PlusCodeResult.model_validate(data)

    async def decode_plus_code(self, code: str) -> PlusCodeResult:
        """Decode a Plus Code to coordinates and bounds."""
        data = await self._request("GET", "/pluscode/decode", params={"code": code})
        return PlusCodeResult.model_validate(data)

    async def validate_plus_code(self, code: str) -> bool:
        """Check if a Plus Code string is valid."""
        data = await self._request("GET", "/pluscode/validate", params={"code": code})
        if isinstance(data, dict):
            return bool(data.get("valid", False))
        return bool(data)

    # ── Islands ──────────────────────────────────────────────────────

    async def list_islands(self) -> list[Island]:
        """List all island groups."""
        data = await self._request("GET", "/islands")
        if isinstance(data, list):
            return [Island.model_validate(item) for item in data]
        return [Island.model_validate(data)]

    async def get_island(self, id_or_name: str) -> Island:
        """Get an island by ID or name."""
        data = await self._request("GET", f"/islands/{quote(id_or_name, safe='')}")
        return Island.model_validate(data)

    async def get_island_stats(self, id_or_name: str) -> IslandStats:
        """Get coverage statistics for a specific island."""
        path = f"/islands/{quote(id_or_name, safe='')}/stats"
        data = await self._request("GET", path)
        return IslandStats.model_validate(data)

    # ── Health ───────────────────────────────────────────────────────

    async def health_check(self) -> HealthStatus:
        """Check API readiness (database + redis)."""
        data = await self._request("GET", "/health/ready")
        return HealthStatus.model_validate(data)

    # ── Lifecycle ────────────────────────────────────────────────────

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()

    async def __aenter__(self) -> LocationRegistryClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    # ── Internal ─────────────────────────────────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        parse_envelope: bool = True,
    ) -> Any:
        """Core request method — runs through circuit breaker + retry."""

        async def _do_request() -> Any:
            response = await self._http.request(method, path, params=params)

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                raise RateLimitError(
                    "Rate limit exceeded",
                    code="RATE_LIMITED",
                    status_code=429,
                    retry_after=float(retry_after) if retry_after else None,
                )

            if response.status_code >= 400:
                error = self._map_error(response.status_code, response.json())
                if response.status_code in _NON_RETRYABLE_CODES:
                    raise error
                # 5xx — wrap for retry
                raise _ServerError(error)

            body = response.json()

            if parse_envelope and isinstance(body, dict) and "data" in body:
                return body["data"]
            if not parse_envelope:
                return body
            return body

        try:
            retrying = retry(
                stop=stop_after_attempt(self._max_retries),
                wait=wait_exponential_jitter(initial=0.5, max=4.0, jitter=0.5),
                retry=retry_if_exception_type((_ServerError, httpx.TransportError)),
                reraise=True,
            )
            return await self._circuit.call(retrying(_do_request))
        except _ServerError as exc:
            raise exc.original from exc

    @staticmethod
    def _map_error(status_code: int, body: Any) -> LocationRegistryError:
        """Map HTTP error responses to typed exceptions."""
        if isinstance(body, dict):
            error_obj = body.get("error", {})
            if isinstance(error_obj, dict):
                message = error_obj.get("message", f"HTTP {status_code}")
                code = error_obj.get("code", "UNKNOWN")
            else:
                message = str(body.get("message", f"HTTP {status_code}"))
                code = "UNKNOWN"
        else:
            message = f"HTTP {status_code}"
            code = "UNKNOWN"

        kwargs: dict[str, Any] = {"code": code, "status_code": status_code}

        if status_code == 404:
            return NotFoundError(message, **kwargs)
        if status_code in (400, 422):
            return ValidationError(message, **kwargs)
        if status_code in (401, 403):
            return AuthError(message, **kwargs)
        if status_code == 503:
            return ServiceUnavailableError(message, **kwargs)
        return LocationRegistryError(message, **kwargs)


def _build_params(**kwargs: Any) -> dict[str, Any]:
    """Build query params dict, excluding None values."""
    return {k: v for k, v in kwargs.items() if v is not None}


def _parse_paginated(envelope: Any, model_class: type[Any]) -> PaginatedResult[Any]:
    """Parse API paginated envelope into PaginatedResult."""
    if isinstance(envelope, dict):
        data_list = envelope.get("data", [])
        meta = envelope.get("meta", {})
        pagination = meta.get("pagination", {}) if isinstance(meta, dict) else {}
    else:
        data_list = []
        pagination = {}

    items = [model_class.model_validate(item) for item in data_list]

    return PaginatedResult(
        data=items,
        next_cursor=pagination.get("next_cursor"),
        has_more=pagination.get("has_more", False),
        total=pagination.get("total"),
    )
