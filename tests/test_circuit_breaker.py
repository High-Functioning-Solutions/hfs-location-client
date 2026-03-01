"""Tests for the async circuit breaker."""

import pytest

from hfs_location_client._circuit_breaker import CircuitBreaker, CircuitState
from hfs_location_client.exceptions import CircuitOpenError


async def _succeed() -> str:
    return "ok"


async def _fail() -> str:
    raise RuntimeError("boom")


async def test_starts_closed() -> None:
    cb = CircuitBreaker(failure_threshold=3)
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


async def test_success_keeps_closed() -> None:
    cb = CircuitBreaker(failure_threshold=3)
    result = await cb.call(_succeed)
    assert result == "ok"
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


async def test_opens_after_threshold_failures() -> None:
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)

    for _ in range(3):
        with pytest.raises(RuntimeError):
            await cb.call(_fail)

    assert cb.state == CircuitState.OPEN
    assert cb.failure_count == 3


async def test_open_circuit_raises_circuit_open_error() -> None:
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)

    with pytest.raises(RuntimeError):
        await cb.call(_fail)

    assert cb.state == CircuitState.OPEN

    with pytest.raises(CircuitOpenError):
        await cb.call(_succeed)


async def test_success_resets_failure_count() -> None:
    cb = CircuitBreaker(failure_threshold=3)

    # Two failures
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await cb.call(_fail)
    assert cb.failure_count == 2

    # One success resets
    await cb.call(_succeed)
    assert cb.failure_count == 0
    assert cb.state == CircuitState.CLOSED


async def test_half_open_after_recovery_timeout() -> None:
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.0)

    with pytest.raises(RuntimeError):
        await cb.call(_fail)
    assert cb.state == CircuitState.OPEN

    # Recovery timeout is 0, so it should transition to half-open
    result = await cb.call(_succeed)
    assert result == "ok"
    assert cb.state == CircuitState.CLOSED


async def test_half_open_failure_reopens() -> None:
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.0)

    with pytest.raises(RuntimeError):
        await cb.call(_fail)
    assert cb.state == CircuitState.OPEN

    # Half-open probe fails → reopens
    with pytest.raises(RuntimeError):
        await cb.call(_fail)
    assert cb.state == CircuitState.OPEN


async def test_manual_reset() -> None:
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)

    with pytest.raises(RuntimeError):
        await cb.call(_fail)
    assert cb.state == CircuitState.OPEN

    cb.reset()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0
