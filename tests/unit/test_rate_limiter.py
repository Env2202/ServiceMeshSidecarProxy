# tests/unit/test_rate_limiter.py
# TDD: Tests written FIRST to define expected behavior
# Run: python3 -m pytest tests/unit/test_rate_limiter.py -v -o "addopts="

import pytest

# TDD Red: import fails until sidecar.pipeline.rate_limit is implemented
from sidecar.pipeline.rate_limit import TokenBucketRateLimiter, RateLimiter


class TestTokenBucketRateLimiter:
    """Test token bucket rate limiting algorithm."""

    def test_allows_requests_under_limit(self):
        """Should allow requests when tokens available."""
        pass

    def test_rejects_when_bucket_empty(self):
        """Should reject when no tokens available."""
        pass

    def test_refills_over_time(self):
        """Tokens should refill at configured rate."""
        pass

    def test_burst_allows_spike(self):
        """Burst size should allow temporary spikes."""
        pass

    def test_per_client_limiting(self):
        """Should track limits per client key."""
        pass

    def test_global_limit(self):
        """Global scope limits total across all clients."""
        pass

    def test_route_scope_limit(self):
        """Route scope limits per route."""
        pass


class TestRateLimiterConfiguration:
    """Test rate limiter configuration."""

    def test_configurable_rate(self):
        """Rate (requests per second) should be configurable."""
        pass

    def test_configurable_burst(self):
        """Burst size should be configurable."""
        pass

    def test_configurable_scope(self):
        """Scope (global, client, route) should be configurable."""
        pass
