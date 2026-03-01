"""Async circuit breaker for Location Registry client.

Three states: CLOSED → OPEN → HALF_OPEN → CLOSED.
When failure_threshold consecutive failures occur, the circuit opens.
After recovery_timeout seconds, one probe request is allowed (half-open).
If the probe succeeds, circuit closes; if it fails, circuit re-opens.
"""

from __future__ import annotations

import asyncio
import time
from enum import Enum
from typing import Any, Callable, Coroutine, TypeVar

from hfs_location_client.exceptions import CircuitOpenError

T = TypeVar("T")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Async circuit breaker with counter-based failure tracking."""

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
    ) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._last_failure_time: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    async def call(
        self,
        func: Callable[..., Coroutine[Any, Any, T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute an async function through the circuit breaker."""
        async with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                else:
                    raise CircuitOpenError()

        try:
            result = await func(*args, **kwargs)
        except Exception:
            await self._record_failure()
            raise

        await self._record_success()
        return result

    async def _record_failure(self) -> None:
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if self._failure_count >= self._failure_threshold:
                self._state = CircuitState.OPEN

    async def _record_success(self) -> None:
        async with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED

    def _should_attempt_reset(self) -> bool:
        elapsed = time.monotonic() - self._last_failure_time
        return elapsed >= self._recovery_timeout

    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
