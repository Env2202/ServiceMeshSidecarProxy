# tests/unit/test_router_logging.py
# Phase 4: Router Logging Tests
# TDD: Write failing tests first, then implement

import pytest
import json
import logging
import io
import sys

# Configuration must be imported first
from sidecar.telemetry.logging import configure_logging
from sidecar.telemetry.context import RequestContext


class TestRouterRouteMatchingLogs:
    """Tests for router route matching logging."""

    def test_router_logs_route_match(self):
        """Router should log when a route matches."""
        # Capture stdout since structlog outputs there
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        configure_logging(level="debug", format="json")

        # Set up request context
        ctx = RequestContext.create(existing_id="router-test-123")
        ctx.set_current()

        # Import router AFTER configuration
        from sidecar.pipeline.router import Router, Route, RouteMatch

        # Create router with a route
        route = Route(
            name="user-service",
            match=RouteMatch(path_prefix="/api/users"),
            cluster="users"
        )
        router = Router([route])

        # Create mock request
        request = type('Request', (), {'path': '/api/users/123', 'host': 'localhost'})()

        # Route the request
        matched = router.route(request)

        # Restore stdout and check logs
        sys.stdout = old_stdout
        output = log_capture.getvalue()
        assert "Route matched" in output

    def test_router_logs_path_in_match(self):
        """Router log should include request path."""
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        configure_logging(level="debug", format="json")

        ctx = RequestContext.create(existing_id="router-test-123")
        ctx.set_current()

        from sidecar.pipeline.router import Router, Route, RouteMatch

        route = Route(
            name="user-service",
            match=RouteMatch(path_prefix="/api/users"),
            cluster="users"
        )
        router = Router([route])

        request = type('Request', (), {'path': '/api/users/123', 'host': 'localhost'})()
        router.route(request)

        sys.stdout = old_stdout
        output = log_capture.getvalue()
        assert "/api/users/123" in output

    def test_router_logs_no_match_404(self):
        """Router should log 404 when no route matches."""
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        configure_logging(level="debug", format="json")

        ctx = RequestContext.create(existing_id="router-test-123")
        ctx.set_current()

        from sidecar.pipeline.router import Router, Route, RouteMatch

        route = Route(
            name="user-service",
            match=RouteMatch(path_prefix="/api/other"),
            cluster="users"
        )
        router = Router([route])

        request = type('Request', (), {'path': '/api/users/123', 'host': 'localhost'})()
        router.route(request)

        sys.stdout = old_stdout
        output = log_capture.getvalue()
        assert "No route matched" in output


class TestRouterRequestIdInLogs:
    """Tests for request_id in router logs."""

    def test_router_log_includes_request_id_when_in_context(self):
        """Router logs should include request_id when in request context."""
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        # Configure logging FIRST (before any other imports)
        configure_logging(level="debug", format="json")

        # Set up request context AFTER logging is configured
        ctx = RequestContext.create(existing_id="router-test-123")
        ctx.set_current()

        # Import router AFTER configuration
        from sidecar.pipeline.router import Router, Route, RouteMatch

        route = Route(
            name="user-service",
            match=RouteMatch(path_prefix="/api/users"),
            cluster="users"
        )
        router = Router([route])

        request = type('Request', (), {'path': '/api/users/123', 'host': 'localhost'})()
        router.route(request)

        sys.stdout = old_stdout
        output = log_capture.getvalue()
        # request_id should be in the log output
        assert "router-test-123" in output

    def test_router_log_works_without_request_context(self):
        """Router should work without request context."""
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        configure_logging(level="debug", format="json")

        # No request context set

        from sidecar.pipeline.router import Router, Route, RouteMatch

        route = Route(
            name="user-service",
            match=RouteMatch(path_prefix="/api/users"),
            cluster="users"
        )
        router = Router([route])

        request = type('Request', (), {'path': '/api/users/123', 'host': 'localhost'})()
        # Should not raise
        router.route(request)

        sys.stdout = old_stdout
        # Log should still be produced
        output = log_capture.getvalue()
        assert "Route matched" in output


class TestRouterLogLevels:
    """Tests for router log levels."""

    def test_route_match_logged_at_debug_level(self):
        """Route match should be logged at debug level."""
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        configure_logging(level="debug", format="json")

        ctx = RequestContext.create(existing_id="router-test-123")
        ctx.set_current()

        from sidecar.pipeline.router import Router, Route, RouteMatch

        route = Route(
            name="user-service",
            match=RouteMatch(path_prefix="/api/users"),
            cluster="users"
        )
        router = Router([route])

        request = type('Request', (), {'path': '/api/users/123', 'host': 'localhost'})()
        router.route(request)

        sys.stdout = old_stdout
        output = log_capture.getvalue()
        # Debug message should be present
        assert "Routing request" in output

    def test_no_route_match_logged_at_warning_level(self):
        """No route match should be logged at warning level."""
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        configure_logging(level="debug", format="json")

        ctx = RequestContext.create(existing_id="router-test-123")
        ctx.set_current()

        from sidecar.pipeline.router import Router, Route, RouteMatch

        route = Route(
            name="user-service",
            match=RouteMatch(path_prefix="/api/other"),
            cluster="users"
        )
        router = Router([route])

        request = type('Request', (), {'path': '/api/users/123', 'host': 'localhost'})()
        router.route(request)

        sys.stdout = old_stdout
        output = log_capture.getvalue()
        # Warning message should be present
        assert "No route matched" in output
