# sidecar/pipeline/circuit_breaker.py - Circuit breaker pattern
# Implements fail-fast protection per plan

from enum import Enum
from typing import Optional
import asyncio
import time

from ..telemetry.logging import get_logger

logger = get_logger("circuit_breaker")


class State(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Failing - reject requests
    HALF_OPEN = "HALF_OPEN"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker to protect against cascading failures."""

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        timeout: float = 30.0,
        volume_threshold: int = 10,
        failure_rate_threshold: float = 0.5
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.volume_threshold = volume_threshold
        self.failure_rate_threshold = failure_rate_threshold

        self.state = State.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self.total_requests = 0
        self.total_failures = 0

    def allow_request(self) -> bool:
        """Determine if a request should be allowed."""
        if self.state == State.CLOSED:
            return True
        elif self.state == State.OPEN:
            # Check if timeout has passed
            if time.time() - self.last_failure_time > self.timeout:
                logger.info(
                    "Circuit breaker transitioning to HALF_OPEN",
                    failure_count=self.failure_count
                )
                self.state = State.HALF_OPEN
                return True
            logger.debug("Circuit breaker OPEN - request rejected")
            return False
        elif self.state == State.HALF_OPEN:
            return True  # Allow one test request
        return False

    async def record_success(self):
        """Record a successful request."""
        self.success_count += 1
        self.total_requests += 1

        if self.state == State.HALF_OPEN:
            if self.success_count >= self.success_threshold:
                logger.info(
                    "Circuit breaker CLOSED - service recovered",
                    success_count=self.success_count
                )
                self.state = State.CLOSED
                self.reset()

        self.success_count = min(self.success_count, self.success_threshold)

    async def record_failure(self):
        """Record a failed request."""
        self.failure_count += 1
        self.total_failures += 1
        self.total_requests += 1
        self.last_failure_time = time.time()

        if self.state == State.CLOSED:
            if (self.failure_count >= self.failure_threshold or
                (self.total_requests >= self.volume_threshold and
                 self.total_failures / self.total_requests >= self.failure_rate_threshold)):
                logger.warning(
                    "Circuit breaker OPENED - too many failures",
                    failure_count=self.failure_count,
                    failure_rate=self.total_failures / self.total_requests if self.total_requests > 0 else 0
                )
                self.state = State.OPEN
        elif self.state == State.HALF_OPEN:
            logger.warning("Circuit breaker OPENED - failure in half-open state")
            self.state = State.OPEN
            self.success_count = 0

        self.failure_count = min(self.failure_count, self.failure_threshold)

    def reset(self):
        """Reset circuit breaker to closed state."""
        self.state = State.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.total_requests = 0
        self.total_failures = 0

    def get_state(self) -> State:
        """Get current state."""
        return self.state

    @property
    def is_open(self) -> bool:
        """Check if circuit breaker is open."""
        return self.state == State.OPEN

    @property
    def is_closed(self) -> bool:
        """Check if circuit breaker is closed."""
        return self.state == State.CLOSED

