# tests/unit/test_health_checker.py
# TDD: Tests written FIRST to define expected behavior
# Run: python3 -m pytest tests/unit/test_health_checker.py -v -o "addopts="

import pytest

# TDD Red: import fails until sidecar.health.checker/tracker is implemented
from sidecar.health.checker import HealthChecker, HealthStatus
from sidecar.health.tracker import PassiveHealthTracker


class TestActiveHealthChecks:
    """Test active health checking (probes)."""

    def test_http_probe_succeeds_on_200(self):
        """HTTP probe should pass on 200 response."""
        pass

    def test_http_probe_fails_on_5xx(self):
        """HTTP probe should fail on 5xx response."""
        pass

    def test_http_probe_fails_on_timeout(self):
        """HTTP probe should fail on timeout."""
        pass

    def test_configurable_probe_interval(self):
        """Probe interval should be configurable."""
        pass

    def test_configurable_probe_timeout(self):
        """Probe timeout should be configurable."""
        pass

    def test_configurable_healthy_threshold(self):
        """Healthy threshold (consecutive successes) should be configurable."""
        pass

    def test_configurable_unhealthy_threshold(self):
        """Unhealthy threshold (consecutive failures) should be configurable."""
        pass


class TestPassiveHealthTracking:
    """Test passive health tracking (eject on failures)."""

    def test_ejects_endpoint_after_consecutive_failures(self):
        """Should eject endpoint after N consecutive failures."""
        pass

    def test_readds_endpoint_after_recovery(self):
        """Should re-add endpoint after successful requests."""
        pass

    def test_tracks_per_endpoint(self):
        """Should track failures per endpoint."""
        pass

    def test_configurable_ejection_threshold(self):
        """Ejection threshold should be configurable."""
        pass
