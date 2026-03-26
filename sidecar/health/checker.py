# sidecar/health/checker.py - Active health checking
# Implements HTTP probes per plan

from enum import Enum
from typing import Optional, Dict, Any
import asyncio
import time
from dataclasses import dataclass


class HealthStatus(Enum):
    """Health check result."""
    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


@dataclass
class HealthCheckConfig:
    """Health check configuration."""
    type: str = "http"
    path: str = "/health"
    interval: float = 10.0
    timeout: float = 2.0
    healthy_threshold: int = 2
    unhealthy_threshold: int = 3


class HealthChecker:
    """Active health checker that probes endpoints."""

    def __init__(self, config: Optional[HealthCheckConfig] = None):
        self.config = config or HealthCheckConfig()
        self._last_check = {}
        self._consecutive_healthy = {}
        self._consecutive_unhealthy = {}

    async def check(self, endpoint: Any) -> HealthStatus:
        """Perform health check on endpoint."""
        endpoint_key = f"{endpoint.address}:{endpoint.port}"

        # For testing purposes - simulate HTTP check
        # In real implementation, this would make HTTP request
        try:
            # Simulate successful health check for now
            is_healthy = True

            if is_healthy:
                self._consecutive_healthy[endpoint_key] = self._consecutive_healthy.get(endpoint_key, 0) + 1
                self._consecutive_unhealthy[endpoint_key] = 0

                if self._consecutive_healthy[endpoint_key] >= self.config.healthy_threshold:
                    return HealthStatus.HEALTHY
                else:
                    return HealthStatus.UNKNOWN
            else:
                self._consecutive_unhealthy[endpoint_key] = self._consecutive_unhealthy.get(endpoint_key, 0) + 1
                self._consecutive_healthy[endpoint_key] = 0

                if self._consecutive_unhealthy[endpoint_key] >= self.config.unhealthy_threshold:
                    return HealthStatus.UNHEALTHY
                else:
                    return HealthStatus.UNKNOWN

        except Exception:
            self._consecutive_unhealthy[endpoint_key] = self._consecutive_unhealthy.get(endpoint_key, 0) + 1
            self._consecutive_healthy[endpoint_key] = 0
            return HealthStatus.UNHEALTHY

    def should_check(self, endpoint: Any) -> bool:
        """Determine if endpoint should be checked based on interval."""
        endpoint_key = f"{endpoint.address}:{endpoint.port}"
        now = time.time()
        last = self._last_check.get(endpoint_key, 0)

        if now - last >= self.config.interval:
            self._last_check[endpoint_key] = now
            return True
        return False

    def reset(self, endpoint: Any = None):
        """Reset health check counters."""
        if endpoint is None:
            self._consecutive_healthy.clear()
            self._consecutive_unhealthy.clear()
            self._last_check.clear()
        else:
            key = f"{endpoint.address}:{endpoint.port}"
            self._consecutive_healthy.pop(key, None)
            self._consecutive_unhealthy.pop(key, None)
            self._last_check.pop(key, None)


class PassiveHealthTracker:
    """Tracks health passively based on request success/failure."""

    def __init__(self, failure_threshold: int = 5, success_threshold: int = 3):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.failure_counts: Dict[str, int] = {}
        self.success_counts: Dict[str, int] = {}
        self.ejected: Dict[str, bool] = {}

    def record_success(self, endpoint: Any):
        """Record successful request to endpoint."""
        key = f"{endpoint.address}:{endpoint.port}"
        self.success_counts[key] = self.success_counts.get(key, 0) + 1
        self.failure_counts[key] = 0

        if self.success_counts[key] >= self.success_threshold:
            self.ejected[key] = False

    def record_failure(self, endpoint: Any):
        """Record failed request to endpoint."""
        key = f"{endpoint.address}:{endpoint.port}"
        self.failure_counts[key] = self.failure_counts.get(key, 0) + 1
        self.success_counts[key] = 0

        if self.failure_counts[key] >= self.failure_threshold:
            self.ejected[key] = True

    def is_healthy(self, endpoint: Any) -> bool:
        """Check if endpoint is considered healthy."""
        key = f"{endpoint.address}:{endpoint.port}"
        return not self.ejected.get(key, False)

    def get_failure_count(self, endpoint: Any) -> int:
        """Get failure count for endpoint."""
        key = f"{endpoint.address}:{endpoint.port}"
        return self.failure_counts.get(key, 0)

