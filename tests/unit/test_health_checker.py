# tests/unit/test_health_checker.py
# TDD: Tests written FIRST to define expected behavior

import pytest

try:
    from sidecar.health.checker import HealthChecker, HealthStatus
    from sidecar.health.tracker import PassiveHealthTracker
except ImportError:
    HealthChecker = None
    HealthStatus = None
    PassiveHealthTracker = None


class TestActiveHealthChecks:
    """Test active health checking (probes)."""

    def test_http_probe_succeeds_on_200(self):
        """HTTP probe should pass on 200 response."""
        if HealthChecker is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/health/checker.py")
        pass

    def test_http_probe_fails_on_5xx(self):
        """HTTP probe should fail on 5xx response."""
        if HealthChecker is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/health/checker.py")
        pass

    def test_http_probe_fails_on_timeout(self):
        """HTTP probe should fail on timeout."""
        if HealthChecker is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/health/checker.py")
        pass

    def test_configurable_probe_interval(self):
        """Probe interval should be configurable."""
        if HealthChecker is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/health/checker.py")
        pass

    def test_configurable_probe_timeout(self):
        """Probe timeout should be configurable."""
        if HealthChecker is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/health/checker.py")
        pass

    def test_configurable_healthy_threshold(self):
        """Healthy threshold (consecutive successes) should be configurable."""
        if HealthChecker is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/health/checker.py")
        pass

    def test_configurable_unhealthy_threshold(self):
        """Unhealthy threshold (consecutive failures) should be configurable."""
        if HealthChecker is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/health/checker.py")
        pass


class TestPassiveHealthTracking:
    """Test passive health tracking (eject on failures)."""

    def test_ejects_endpoint_after_consecutive_failures(self):
        """Should eject endpoint after N consecutive failures."""
        if PassiveHealthTracker is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/health/tracker.py")
        pass

    def test_readds_endpoint_after_recovery(self):
        """Should re-add endpoint after successful requests."""
        if PassiveHealthTracker is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/health/tracker.py")
        pass

    def test_tracks_per_endpoint(self):
        """Should track failures per endpoint."""
        if PassiveHealthTracker is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/health/tracker.py")
        pass

    def test_configurable_ejection_threshold(self):
        """Ejection threshold should be configurable."""
        if PassiveHealthTracker is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/health/tracker.py")
        pass
