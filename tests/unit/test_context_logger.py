# tests/unit/test_context_logger.py
# Phase 2: Context-Aware Logger Tests
# TDD: Write failing tests first, then implement

import pytest
import json
import logging
import io
from unittest.mock import patch, MagicMock

import structlog

from sidecar.telemetry.logging import get_logger, configure_logging
from sidecar.telemetry.context import RequestContext


class TestGetLoggerReturnsBoundLogger:
    """Tests for get_logger() return type."""

    def test_get_logger_returns_bound_logger(self):
        """get_logger() should return a structlog BoundLogger."""
        configure_logging()
        logger = get_logger("test-component")

        assert isinstance(logger, structlog.stdlib.BoundLogger)

    def test_get_logger_without_component(self):
        """get_logger() without component should use default."""
        configure_logging()
        logger = get_logger()

        assert logger is not None

    def test_get_logger_with_component_name(self):
        """get_logger(component) should bind component name."""
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        root_logger = logging.getLogger()
        root_logger.handlers = []
        root_logger.addHandler(handler)

        configure_logging(level="debug", format="json")
        logger = get_logger("router")
        logger.info("test message")

        output = log_capture.getvalue()
        log_entry = json.loads(output.strip())
        assert log_entry["component"] == "router"


class TestLoggerWithRequestContext:
    """Tests for logger behavior with request context."""

    def test_logger_includes_request_id_when_in_context(self):
        """Logger should include request_id when inside request context."""
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        root_logger = logging.getLogger()
        root_logger.handlers = []
        root_logger.addHandler(handler)

        configure_logging(level="debug", format="json")

        # Set up request context
        ctx = RequestContext.create(existing_id="test-req-123")
        ctx.set_current()

        logger = get_logger("test")
        logger.info("test message")

        output = log_capture.getvalue()
        log_entry = json.loads(output.strip())
        assert log_entry["request_id"] == "test-req-123"

    def test_logger_works_without_request_context(self):
        """Logger should work without request context (no errors)."""
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        root_logger = logging.getLogger()
        root_logger.handlers = []
        root_logger.addHandler(handler)

        configure_logging(level="debug", format="json")

        # No request context set
        logger = get_logger("test")
        logger.info("test message")  # Should not raise

        output = log_capture.getvalue()
        log_entry = json.loads(output.strip())
        assert log_entry["event"] == "test message"
        # When no context, request_id should not be in log
        # (or it might be null, depending on implementation)

    @pytest.mark.asyncio
    async def test_logger_includes_request_id_in_async_context(self):
        """Logger should include request_id in async request context."""
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        root_logger = logging.getLogger()
        root_logger.handlers = []
        root_logger.addHandler(handler)

        configure_logging(level="debug", format="json")

        async def process_request():
            ctx = RequestContext.create(existing_id="async-req-456")
            ctx.set_current()

            logger = get_logger("test")
            logger.info("async message")

        await process_request()

        output = log_capture.getvalue()
        log_entry = json.loads(output.strip())
        assert log_entry["request_id"] == "async-req-456"


class TestLoggerBinding:
    """Tests for logger binding capabilities."""

    def test_logger_bind_adds_extra_fields(self):
        """logger.bind() should add extra fields to log entries."""
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        root_logger = logging.getLogger()
        root_logger.handlers = []
        root_logger.addHandler(handler)

        configure_logging(level="debug", format="json")

        logger = get_logger("test")
        bound_logger = logger.bind(user_id="123", action="create")
        bound_logger.info("user action")

        output = log_capture.getvalue()
        log_entry = json.loads(output.strip())
        assert log_entry["user_id"] == "123"
        assert log_entry["action"] == "create"

    def test_logger_bind_preserves_component(self):
        """logger.bind() should preserve component name."""
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        root_logger = logging.getLogger()
        root_logger.handlers = []
        root_logger.addHandler(handler)

        configure_logging(level="debug", format="json")

        logger = get_logger("router")
        bound_logger = logger.bind(route="/api/users")
        bound_logger.info("routing")

        output = log_capture.getvalue()
        log_entry = json.loads(output.strip())
        assert log_entry["component"] == "router"
        assert log_entry["route"] == "/api/users"


class TestLoggerMethods:
    """Tests for different logger methods (debug, info, warning, error)."""

    def test_logger_debug(self):
        """Logger debug method should work correctly."""
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        root_logger = logging.getLogger()
        root_logger.handlers = []
        root_logger.addHandler(handler)

        configure_logging(level="debug", format="json")
        logger = get_logger("test")
        logger.debug("debug message")

        assert "debug message" in log_capture.getvalue()

    def test_logger_info(self):
        """Logger info method should work correctly."""
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        root_logger = logging.getLogger()
        root_logger.handlers = []
        root_logger.addHandler(handler)

        configure_logging(level="debug", format="json")
        logger = get_logger("test")
        logger.info("info message")

        assert "info message" in log_capture.getvalue()

    def test_logger_warning(self):
        """Logger warning method should work correctly."""
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        root_logger = logging.getLogger()
        root_logger.handlers = []
        root_logger.addHandler(handler)

        configure_logging(level="debug", format="json")
        logger = get_logger("test")
        logger.warning("warning message")

        assert "warning message" in log_capture.getvalue()

    def test_logger_error(self):
        """Logger error method should work correctly."""
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        root_logger = logging.getLogger()
        root_logger.handlers = []
        root_logger.addHandler(handler)

        configure_logging(level="debug", format="json")
        logger = get_logger("test")
        logger.error("error message")

        assert "error message" in log_capture.getvalue()

    def test_logger_exception(self):
        """Logger exception method should include exception info."""
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        root_logger = logging.getLogger()
        root_logger.handlers = []
        root_logger.addHandler(handler)

        configure_logging(level="debug", format="json")

        logger = get_logger("test")
        try:
            raise ValueError("test error")
        except:
            logger.exception("error occurred")

        output = log_capture.getvalue()
        assert "error occurred" in output
        assert "ValueError" in output
