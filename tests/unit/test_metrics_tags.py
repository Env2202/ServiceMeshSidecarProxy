# tests/unit/test_metrics_tags.py
# Phase 6: Metrics Tagging Tests (Optional Enhancement)
# TDD: Write failing tests first, then implement

import pytest


class TestMetricsRequestIdTagging:
    """Tests for request_id tagging in metrics (optional)."""

    def test_metrics_can_include_request_id_tag(self):
        """Metrics should be able to include request_id tag."""
        # TODO: Import and test once implemented
        # from sidecar.telemetry.metrics import MetricsCollector
        # from sidecar.telemetry.context import RequestContext
        #
        # ctx = RequestContext.create(existing_id="metrics-test-123")
        # ctx.set_current()
        #
        # metrics = MetricsCollector()
        # metrics.record_request(
        #     method="GET",
        #     route="users",
        #     status_code=200,
        #     duration=0.1,
        #     include_request_id=True
        # )
        #
        # # Verify metric was recorded with request_id
        pytest.fail("Test not yet implemented - optional metrics enhancement")

    def test_metrics_respect_cardinality_limits(self):
        """Metrics collection should respect cardinality limits."""
        # TODO: Import and test once implemented
        pytest.fail("Test not yet implemented - optional metrics enhancement")

    def test_metrics_request_id_tag_optional(self):
        """Request ID tagging should be optional (off by default)."""
        # TODO: Import and test once implemented
        pytest.fail("Test not yet implemented - optional metrics enhancement")


class TestMetricsWithoutRequestId:
    """Tests for metrics without request_id (default behavior)."""

    def test_default_metrics_no_request_id(self):
        """Default metrics should not include request_id to prevent explosion."""
        # TODO: Import and test once implemented
        pytest.fail("Test not yet implemented - optional metrics enhancement")
