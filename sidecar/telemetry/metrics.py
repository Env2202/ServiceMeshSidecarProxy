# sidecar/telemetry/metrics.py - Prometheus metrics
# Implements metrics collection for POC (Prometheus only)

from prometheus_client import Counter, Histogram, Gauge, generate_latest
from typing import Dict, Any
import time


class MetricsCollector:
    """Prometheus metrics collector for sidecar proxy."""

    def __init__(self):
        # Request metrics
        self.request_counter = Counter(
            'sidecar_requests_total',
            'Total number of requests',
            ['method', 'route', 'status']
        )

        self.request_latency = Histogram(
            'sidecar_request_duration_seconds',
            'Request latency in seconds',
            ['method', 'route']
        )

        self.error_counter = Counter(
            'sidecar_errors_total',
            'Total number of errors',
            ['type', 'route']
        )

        # Circuit breaker metrics
        self.circuit_breaker_state = Gauge(
            'sidecar_circuit_breaker_state',
            'Circuit breaker state (0=closed, 1=open, 2=half-open)',
            ['route']
        )

        # Rate limiting metrics
        self.rate_limit_hits = Counter(
            'sidecar_rate_limit_hits_total',
            'Number of rate limit hits',
            ['client', 'route']
        )

        # Health check metrics
        self.health_check_results = Counter(
            'sidecar_health_check_results_total',
            'Health check results',
            ['endpoint', 'result']
        )

    def record_request(self, method: str, route: str, status_code: int, duration: float):
        """Record a request with latency and status."""
        self.request_counter.labels(
            method=method,
            route=route,
            status=status_code
        ).inc()

        self.request_latency.labels(
            method=method,
            route=route
        ).observe(duration)

        if status_code >= 400:
            error_type = "client_error" if status_code < 500 else "server_error"
            self.error_counter.labels(
                type=error_type,
                route=route
            ).inc()

    def record_circuit_breaker_state(self, route: str, state: str):
        """Record circuit breaker state."""
        state_value = 0
        if state == "OPEN":
            state_value = 1
        elif state == "HALF_OPEN":
            state_value = 2

        self.circuit_breaker_state.labels(route=route).set(state_value)

    def record_rate_limit(self, client: str, route: str):
        """Record rate limit hit."""
        self.rate_limit_hits.labels(client=client, route=route).inc()

    def record_health_check(self, endpoint: str, is_healthy: bool):
        """Record health check result."""
        result = "healthy" if is_healthy else "unhealthy"
        self.health_check_results.labels(endpoint=endpoint, result=result).inc()

    def get_metrics(self) -> str:
        """Get metrics in Prometheus text format."""
        return generate_latest().decode('utf-8')

    def reset(self):
        """Reset all metrics (for testing)."""
        # This is mainly for testing purposes
        pass

