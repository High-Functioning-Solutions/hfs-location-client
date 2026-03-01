"""Shared utilities for async and sync clients.

Extracted to avoid code duplication between LocationRegistryClient
and LocationRegistrySyncClient.
"""

from __future__ import annotations

from typing import Any

from hfs_location_client.exceptions import (
    AuthError,
    LocationRegistryError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from hfs_location_client.models import PaginatedResult

# 4xx errors should NOT be retried
NON_RETRYABLE_CODES = {400, 401, 403, 404, 422}


class ServerError(Exception):
    """Internal wrapper for 5xx errors that should trigger retry."""

    def __init__(self, original: LocationRegistryError) -> None:
        self.original = original
        super().__init__(str(original))


def map_error(
    status_code: int, body: Any,
) -> LocationRegistryError:
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


def build_params(**kwargs: Any) -> dict[str, Any]:
    """Build query params dict, excluding None values."""
    return {k: v for k, v in kwargs.items() if v is not None}


def parse_paginated(
    envelope: Any, model_class: type[Any],
) -> PaginatedResult[Any]:
    """Parse API paginated envelope into PaginatedResult."""
    if isinstance(envelope, dict):
        data_list = envelope.get("data", [])
        meta = envelope.get("meta", {})
        pagination = (
            meta.get("pagination", {}) if isinstance(meta, dict) else {}
        )
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
