# tests/unit/test_request_context.py
# Phase 1: Request Context Infrastructure Tests
# TDD: Write failing tests first, then implement

import pytest
import re
import time
import asyncio
from unittest.mock import patch

from sidecar.telemetry.context import RequestContext, REQUEST_ID_CTX, START_TIME_CTX


class TestRequestContextCreate:
    """Tests for RequestContext.create() method."""

    def test_create_generates_unique_request_id(self):
        """RequestContext.create() should generate unique request IDs in format req-<12-char-hex>."""
        ctx1 = RequestContext.create()
        ctx2 = RequestContext.create()

        assert ctx1.request_id != ctx2.request_id
        assert re.match(r'^req-[a-f0-9]{12}$', ctx1.request_id)
        assert re.match(r'^req-[a-f0-9]{12}$', ctx2.request_id)

    def test_create_uses_existing_id_when_provided(self):
        """RequestContext.create(existing_id=...) should use the provided ID."""
        existing_id = "custom-request-id-123"
        ctx = RequestContext.create(existing_id=existing_id)

        assert ctx.request_id == existing_id

    def test_create_generates_new_id_when_existing_is_none(self):
        """RequestContext.create(existing_id=None) should generate new ID."""
        ctx = RequestContext.create(existing_id=None)

        assert ctx.request_id is not None
        assert re.match(r'^req-[a-f0-9]{12}$', ctx.request_id)

    def test_create_sets_start_time(self):
        """RequestContext.create() should set start_time to current time."""
        before = time.time()
        ctx = RequestContext.create()
        after = time.time()

        assert before <= ctx.start_time <= after

    def test_create_with_method_and_path(self):
        """RequestContext.create() should accept optional method and path."""
        ctx = RequestContext.create(method="GET", path="/api/users")

        assert ctx.method == "GET"
        assert ctx.path == "/api/users"


class TestRequestContextSetCurrent:
    """Tests for RequestContext.set_current() method."""

    def test_set_current_sets_context_vars(self):
        """set_current() should set REQUEST_ID_CTX and START_TIME_CTX."""
        ctx = RequestContext.create(method="POST", path="/test")
        ctx.set_current()

        assert REQUEST_ID_CTX.get() == ctx.request_id
        assert START_TIME_CTX.get() == ctx.start_time

    @pytest.mark.asyncio
    async def test_context_isolation_between_coroutines(self):
        """Context vars should be isolated between different coroutines."""
        async def task_a():
            ctx_a = RequestContext.create(existing_id="task-a-id")
            ctx_a.set_current()
            await asyncio.sleep(0.01)
            return REQUEST_ID_CTX.get()

        async def task_b():
            ctx_b = RequestContext.create(existing_id="task-b-id")
            ctx_b.set_current()
            await asyncio.sleep(0.01)
            return REQUEST_ID_CTX.get()

        result_a, result_b = await asyncio.gather(task_a(), task_b())

        assert result_a == "task-a-id"
        assert result_b == "task-b-id"


class TestRequestIdFormat:
    """Tests for request ID format compliance."""

    def test_request_id_prefix(self):
        """Request IDs should start with 'req-' prefix."""
        ctx = RequestContext.create()

        assert ctx.request_id.startswith("req-")

    def test_request_id_hex_length(self):
        """Request IDs should have exactly 12 hex characters after prefix."""
        ctx = RequestContext.create()

        hex_part = ctx.request_id.replace("req-", "")
        assert len(hex_part) == 12
        assert all(c in '0123456789abcdef' for c in hex_part)


class TestContextVarsExist:
    """Tests to verify context variables are properly defined."""

    def test_request_id_ctx_exists(self):
        """REQUEST_ID_CTX context variable should exist."""
        assert REQUEST_ID_CTX is not None

    def test_start_time_ctx_exists(self):
        """START_TIME_CTX context variable should exist."""
        assert START_TIME_CTX is not None
