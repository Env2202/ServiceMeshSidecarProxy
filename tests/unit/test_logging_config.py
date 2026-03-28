# tests/unit/test_logging_config.py
# Phase 2: Logging Configuration Tests
# TDD: Write failing tests first, then implement

import pytest
import json
import logging
import io
import sys
from unittest.mock import patch, MagicMock

from sidecar.telemetry.logging import configure_logging, get_logger


class TestConfigureLogging:
    """Tests for configure_logging() function."""

    def test_configure_logging_sets_up_structlog(self):
        """configure_logging() should properly initialize structlog."""
        import structlog

        configure_logging()

        # Should be able to get a logger after configuration
        logger = structlog.get_logger()
        assert logger is not None

    def test_configure_logging_with_json_format(self):
        """configure_logging(format='json') should produce JSON output."""
        # Capture stdout since structlog outputs there
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        configure_logging(level="debug", format="json")
        logger = get_logger("test")
        logger.info("test message")

        sys.stdout = old_stdout
        output = log_capture.getvalue()
        # Should be valid JSON
        log_entry = json.loads(output.strip())
        assert log_entry["event"] == "test message"

    def test_configure_logging_with_console_format(self):
        """configure_logging(format='console') should produce human-readable output."""
        configure_logging(level="debug", format="console")
        logger = get_logger("test")

        # Console format should be more readable (not strict JSON)
        # This is a basic smoke test
        logger.info("test message")

    def test_configure_logging_sets_log_level(self):
        """configure_logging(level=...) should set the appropriate log level."""
        configure_logging(level="warning")

        # Get the root logger and check level
        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING

    def test_configure_logging_with_invalid_level(self):
        """configure_logging() should handle invalid log levels gracefully."""
        # Invalid level defaults to INFO
        configure_logging(level="invalid_level")
        # Should not raise an exception


class TestLogLevelFiltering:
    """Tests for log level filtering."""

    def test_debug_level_includes_debug_messages(self):
        """Debug level should include debug messages."""
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        configure_logging(level="debug", format="json")
        logger = get_logger("test")
        logger.debug("debug message")

        sys.stdout = old_stdout
        assert "debug message" in log_capture.getvalue()

    def test_info_level_excludes_debug_messages(self):
        """Info level should exclude debug messages."""
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        configure_logging(level="info", format="json")
        logger = get_logger("test")
        logger.debug("debug message")
        logger.info("info message")

        sys.stdout = old_stdout
        output = log_capture.getvalue()
        assert "debug message" not in output
        assert "info message" in output

    def test_warning_level_excludes_info_messages(self):
        """Warning level should exclude info messages."""
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        configure_logging(level="warning", format="json")
        logger = get_logger("test")
        logger.info("info message")
        logger.warning("warning message")

        sys.stdout = old_stdout
        output = log_capture.getvalue()
        assert "info message" not in output
        assert "warning message" in output

    def test_error_level_excludes_warning_messages(self):
        """Error level should exclude warning messages."""
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        configure_logging(level="error", format="json")
        logger = get_logger("test")
        logger.warning("warning message")
        logger.error("error message")

        sys.stdout = old_stdout
        output = log_capture.getvalue()
        assert "warning message" not in output
        assert "error message" in output


class TestJSONFormatterOutput:
    """Tests for JSON formatter output structure."""

    def test_json_output_contains_timestamp(self):
        """JSON log output should contain timestamp field."""
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        configure_logging(level="debug", format="json")
        logger = get_logger("test")
        logger.info("test")

        sys.stdout = old_stdout
        output = log_capture.getvalue()
        log_entry = json.loads(output.strip())
        assert "timestamp" in log_entry

    def test_json_output_contains_level(self):
        """JSON log output should contain level field."""
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        configure_logging(level="debug", format="json")
        logger = get_logger("test")
        logger.info("test")

        sys.stdout = old_stdout
        output = log_capture.getvalue()
        log_entry = json.loads(output.strip())
        assert "level" in log_entry

    def test_json_output_contains_event(self):
        """JSON log output should contain event field."""
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        configure_logging(level="debug", format="json")
        logger = get_logger("test")
        logger.info("test message")

        sys.stdout = old_stdout
        output = log_capture.getvalue()
        log_entry = json.loads(output.strip())
        assert "event" in log_entry
        assert log_entry["event"] == "test message"

    def test_json_output_contains_logger_name(self):
        """JSON log output should contain logger name."""
        old_stdout = sys.stdout
        sys.stdout = log_capture = io.StringIO()

        configure_logging(level="debug", format="json")
        logger = get_logger("test-component")
        logger.info("test")

        sys.stdout = old_stdout
        output = log_capture.getvalue()
        log_entry = json.loads(output.strip())
        assert "logger" in log_entry or "logger_name" in log_entry


class TestMultipleConfigurations:
    """Tests for multiple configure_logging calls."""

    def test_reconfigure_changes_settings(self):
        """Calling configure_logging again should update settings."""
        configure_logging(level="debug")
        configure_logging(level="error")

        root_logger = logging.getLogger()
        assert root_logger.level == logging.ERROR
