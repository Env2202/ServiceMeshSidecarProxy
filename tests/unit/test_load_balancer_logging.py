# tests/unit/test_load_balancer_logging.py
# Phase 4: Load Balancer Logging Tests
# TDD: Write failing tests first, then implement

import pytest
import json
import logging
import io
import sys

from sidecar.telemetry.logging import configure_logging
from sidecar.telemetry.context import RequestContext


class TestLoadBalancerSelectionLogs:
    """Tests for load balancer endpoint selection logging."""

    def test_load_balancer_logs_endpoint_selection(self):
        """Load balancer should log endpoint selection."""
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        configure_logging(level="debug", format="json")

        ctx = RequestContext.create(existing_id="lb-test-123")
        ctx.set_current()

        from sidecar.pipeline.load_balancer import RoundRobinBalancer, Endpoint

        endpoints = [
            Endpoint(address="host1", port=8080),
            Endpoint(address="host2", port=8080)
        ]
        lb = RoundRobinBalancer(endpoints)

        request = type('Request', (), {'path': '/test'})()
        selected = lb.select(request)

        sys.stdout = old_stdout
        output = log_capture.getvalue()
        assert "Selected endpoint" in output
        assert "host1:8080" in output

    def test_load_balancer_logs_algorithm_name(self):
        """Load balancer log should include algorithm name."""
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        configure_logging(level="debug", format="json")

        ctx = RequestContext.create(existing_id="lb-test-123")
        ctx.set_current()

        from sidecar.pipeline.load_balancer import RoundRobinBalancer, Endpoint

        endpoints = [Endpoint(address="host1", port=8080)]
        lb = RoundRobinBalancer(endpoints)

        lb.select(None)

        sys.stdout = old_stdout
        output = log_capture.getvalue()
        assert "round-robin" in output.lower()

    def test_load_balancer_logs_selected_endpoint(self):
        """Load balancer log should include selected endpoint."""
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        configure_logging(level="debug", format="json")

        ctx = RequestContext.create(existing_id="lb-test-123")
        ctx.set_current()

        from sidecar.pipeline.load_balancer import RoundRobinBalancer, Endpoint

        endpoints = [Endpoint(address="host1", port=8080)]
        lb = RoundRobinBalancer(endpoints)

        lb.select(None)

        sys.stdout = old_stdout
        output = log_capture.getvalue()
        assert "host1:8080" in output


class TestLoadBalancerRequestIdInLogs:
    """Tests for request_id in load balancer logs."""

    def test_load_balancer_log_includes_request_id(self):
        """Load balancer logs should include request_id."""
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        configure_logging(level="debug", format="json")

        ctx = RequestContext.create(existing_id="lb-test-123")
        ctx.set_current()

        from sidecar.pipeline.load_balancer import RoundRobinBalancer, Endpoint

        endpoints = [Endpoint(address="host1", port=8080)]
        lb = RoundRobinBalancer(endpoints)

        lb.select(None)

        sys.stdout = old_stdout
        output = log_capture.getvalue()
        assert "lb-test-123" in output


class TestLoadBalancerNoHealthyEndpoints:
    """Tests for load balancer when no healthy endpoints."""

    def test_load_balancer_logs_no_healthy_endpoints(self):
        """Load balancer should log when no healthy endpoints available."""
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        configure_logging(level="debug", format="json")

        ctx = RequestContext.create(existing_id="lb-test-123")
        ctx.set_current()

        from sidecar.pipeline.load_balancer import RoundRobinBalancer, Endpoint

        endpoints = [Endpoint(address="host1", port=8080, healthy=False)]
        lb = RoundRobinBalancer(endpoints)

        lb.select(None)

        sys.stdout = old_stdout
        output = log_capture.getvalue()
        assert "No healthy endpoints" in output
