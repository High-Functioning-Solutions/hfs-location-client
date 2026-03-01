"""Tests for exception hierarchy."""

from datetime import datetime, timezone

from hfs_location_client.exceptions import (
    AuthError,
    CircuitOpenError,
    LocationRegistryError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
)


def test_base_exception_attributes() -> None:
    err = LocationRegistryError(
        "Something failed",
        code="TEST_ERROR",
        status_code=500,
        details={"key": "value"},
    )
    assert err.message == "Something failed"
    assert err.code == "TEST_ERROR"
    assert err.status_code == 500
    assert err.details == {"key": "value"}
    assert str(err) == "Something failed"


def test_not_found_error() -> None:
    err = NotFoundError("Building not found", code="NOT_FOUND", status_code=404)
    assert isinstance(err, LocationRegistryError)
    assert err.status_code == 404


def test_rate_limit_error_with_retry_after() -> None:
    err = RateLimitError(
        "Rate limit exceeded",
        retry_after=30.0,
        code="RATE_LIMITED",
        status_code=429,
    )
    assert err.retry_after == 30.0
    assert err.status_code == 429


def test_circuit_open_error_defaults() -> None:
    err = CircuitOpenError()
    assert err.message == "Circuit breaker is open"
    assert err.code == "CIRCUIT_OPEN"
    assert err.status_code == 503
    assert err.reset_at is None


def test_circuit_open_error_with_reset() -> None:
    reset = datetime.now(timezone.utc)
    err = CircuitOpenError(reset_at=reset)
    assert err.reset_at == reset


def test_all_exceptions_catchable_as_base() -> None:
    exceptions = [
        NotFoundError("x", code="NF", status_code=404),
        ValidationError("x", code="VE", status_code=400),
        AuthError("x", code="AU", status_code=401),
        RateLimitError("x", code="RL", status_code=429),
        ServiceUnavailableError("x", code="SU", status_code=503),
        CircuitOpenError(),
    ]
    for exc in exceptions:
        try:
            raise exc
        except LocationRegistryError:
            pass  # All should be caught by base class
