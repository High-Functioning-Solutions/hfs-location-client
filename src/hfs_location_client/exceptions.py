"""Exception hierarchy for Location Registry client errors.

Maps HTTP error responses to typed exceptions. Full retry/circuit breaker
error mapping logic is added in LRC-04; this establishes the type structure.
"""

from __future__ import annotations

from datetime import datetime


class LocationRegistryError(Exception):
    """Base exception for all LR client errors."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "UNKNOWN",
        status_code: int = 0,
        details: dict[str, object] | None = None,
    ) -> None:
        self.code = code
        self.status_code = status_code
        self.message = message
        self.details = details
        super().__init__(message)


class NotFoundError(LocationRegistryError):
    """Resource not found (HTTP 404)."""


class ValidationError(LocationRegistryError):
    """Request validation failed (HTTP 400/422)."""


class AuthError(LocationRegistryError):
    """Authentication or authorization failed (HTTP 401/403)."""


class RateLimitError(LocationRegistryError):
    """Rate limit exceeded (HTTP 429)."""

    def __init__(
        self,
        message: str,
        *,
        retry_after: float | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(message, **kwargs)  # type: ignore[arg-type]
        self.retry_after = retry_after


class ServiceUnavailableError(LocationRegistryError):
    """Service unavailable (HTTP 503)."""


class CircuitOpenError(LocationRegistryError):
    """Circuit breaker is open — requests are blocked."""

    def __init__(
        self,
        message: str = "Circuit breaker is open",
        *,
        reset_at: datetime | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(message, code="CIRCUIT_OPEN", status_code=503, **kwargs)  # type: ignore[arg-type]
        self.reset_at = reset_at
