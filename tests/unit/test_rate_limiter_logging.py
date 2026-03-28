# tests/unit/test_rate_limiter_logging.py
# Phase 4: Rate Limiter Logging Tests
# TDD: Write failing tests first, then implement

import pytest
import json
import logging
import io
import sys

from sidecar.telemetry.logging import configure_logging
from sidecar.telemetry.context import RequestContext


class TestRateLimiterDecisionLogs:
    """Tests for rate limiter allow/deny decision logging."""

    def test_rate_limiter_logs_allow_decision(self):
        """Rate limiter should log when request is allowed."""
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        configure_logging(level="debug", format="json")

        ctx = RequestContext.create(existing_id="rl-test-123")
        ctx.set_current()

        from sidecar.pipeline.rate_limit import TokenBucketRateLimiter

        rl = TokenBucketRateLimiter(rate=100, burst=200)
        allowed = rl.allow("client-1")

        sys.stdout = old_stdout
        output = log_capture.getvalue()
        assert allowed is True
        assert "Request allowed" in output or "remaining_tokens" in output

    def test_rate_limiter_logs_deny_decision(self):
        """Rate limiter should log when request is denied."""
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        configure_logging(level="debug", format="json")

        ctx = RequestContext.create(existing_id="rl-test-123")
        ctx.set_current()

        from sidecar.pipeline.rate_limit import TokenBucketRateLimiter

        rl = TokenBucketRateLimiter(rate=1, burst=1)
        rl.allow("client-1")  # Consume the only token
        allowed = rl.allow("client-1")  # Should be denied

        sys.stdout = old_stdout
        output = log_capture.getvalue()
        assert allowed is False
        assert "Rate limit exceeded" in output

    def test_rate_limiter_logs_include_limit_info(self):
        """Rate limiter logs should include rate limit info."""
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        configure_logging(level="debug", format="json")

        ctx = RequestContext.create(existing_id="rl-test-123")
        ctx.set_current()

        from sidecar.pipeline.rate_limit import TokenBucketRateLimiter

        rl = TokenBucketRateLimiter(rate=100, burst=200)
        rl.allow("client-1")

        sys.stdout = old_stdout
        output = log_capture.getvalue()
        assert "remaining_tokens" in output


class TestRateLimiterRequestIdInLogs:
    """Tests for request_id in rate limiter logs."""

    def test_rate_limiter_log_includes_request_id(self):
        """Rate limiter logs should include request_id."""
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        configure_logging(level="debug", format="json")

        ctx = RequestContext.create(existing_id="rl-test-123")
        ctx.set_current()

        from sidecar.pipeline.rate_limit import TokenBucketRateLimiter

        rl = TokenBucketRateLimiter(rate=100, burst=200)
        rl.allow("client-1")

        sys.stdout = old_stdout
        output = log_capture.getvalue()
        assert "rl-test-123" in output


class TestRateLimiterClientKey:
    """Tests for client key in rate limiter logs."""

    def test_rate_limiter_log_includes_client_key(self):
        """Rate limiter logs should include client key."""
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        configure_logging(level="debug", format="json")

        ctx = RequestContext.create(existing_id="rl-test-123")
        ctx.set_current()

        from sidecar.pipeline.rate_limit import TokenBucketRateLimiter

        rl = TokenBucketRateLimiter(rate=100, burst=200)
        rl.allow("client-1")

        sys.stdout = old_stdout
        output = log_capture.getvalue()
        assert "client-1" in output
