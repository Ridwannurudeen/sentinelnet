"""Async circuit breaker for failing external dependencies.

Stops the per-call retry-and-log spam when an external service (paymaster, RPC,
IPFS provider, etc.) is degraded for the same reason every time. After
``failure_threshold`` consecutive failures, the breaker OPENs for
``open_seconds``, during which all calls short-circuit to a sentinel return
without touching the dependency. After the window elapses the breaker enters
HALF_OPEN: the next call is allowed through; success closes the breaker,
failure re-opens it for another window.
"""
import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class CircuitOpenError(Exception):
    """Raised when a call is short-circuited because the breaker is OPEN."""


class CircuitBreaker:
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

    def __init__(self, name: str, failure_threshold: int = 5,
                 open_seconds: float = 900.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.open_seconds = open_seconds
        self._state = self.CLOSED
        self._failures = 0
        self._opened_at = 0.0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> str:
        return self._state

    def is_open(self) -> bool:
        return self._state == self.OPEN

    async def allow(self) -> bool:
        """Return True if the caller may proceed; False if short-circuited.

        Auto-transitions OPEN -> HALF_OPEN once the open window has elapsed.
        """
        async with self._lock:
            if self._state == self.CLOSED:
                return True
            if self._state == self.OPEN:
                if time.monotonic() - self._opened_at >= self.open_seconds:
                    self._state = self.HALF_OPEN
                    logger.info(
                        f"circuit '{self.name}' HALF_OPEN — probing"
                    )
                    return True
                return False
            # HALF_OPEN — only one probe in flight at a time
            return True

    async def record_success(self) -> None:
        async with self._lock:
            if self._state != self.CLOSED:
                logger.info(f"circuit '{self.name}' CLOSED — recovered")
            self._state = self.CLOSED
            self._failures = 0
            self._opened_at = 0.0

    async def record_failure(self, reason: str = "") -> None:
        async with self._lock:
            self._failures += 1
            if self._state == self.HALF_OPEN:
                self._state = self.OPEN
                self._opened_at = time.monotonic()
                logger.warning(
                    f"circuit '{self.name}' re-OPENed after probe failure: {reason}"
                )
                return
            if self._failures >= self.failure_threshold and self._state == self.CLOSED:
                self._state = self.OPEN
                self._opened_at = time.monotonic()
                logger.warning(
                    f"circuit '{self.name}' OPEN for {self.open_seconds:.0f}s "
                    f"after {self._failures} failures: {reason}"
                )
