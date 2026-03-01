"""Thread-safe synchronous circuit breaker for Flask/sync consumers.

Same three-state logic as _circuit_breaker.py but uses threading.Lock
instead of asyncio.Lock for thread safety in sync contexts.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, TypeVar

from hfs_location_client._circuit_breaker import CircuitState
from hfs_location_client.exceptions import CircuitOpenError

T = TypeVar("T")


class SyncCircuitBreaker:
    """Thread-safe synchronous circuit breaker."""

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
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def call(
        self,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute a sync function through the circuit breaker."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                else:
                    raise CircuitOpenError()

        try:
            result = func(*args, **kwargs)
        except Exception:
            self._record_failure()
            raise

        self._record_success()
        return result

    def _record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if self._failure_count >= self._failure_threshold:
                self._state = CircuitState.OPEN

    def _record_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED

    def _should_attempt_reset(self) -> bool:
        elapsed = time.monotonic() - self._last_failure_time
        return elapsed >= self._recovery_timeout

    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = 0.0
