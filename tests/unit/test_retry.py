# tests/unit/test_retry.py
# TDD: Tests written FIRST to define expected behavior
# Run: python3 -m pytest tests/unit/test_retry.py -v -o "addopts="

import pytest

# TDD Red: import fails until sidecar.pipeline.retry is implemented
from sidecar.pipeline.retry import RetryHandler, RetryPolicy


class TestRetryLogic:
    """Test retry behavior."""

    def test_retries_on_specified_status_codes(self):
        """Should retry on configured status codes (e.g., 5xx, 429)."""
        pass

    def test_retries_on_connect_failure(self):
        """Should retry on connection failure."""
        pass

    def test_retries_on_reset(self):
        """Should retry on connection reset."""
        pass

    def test_does_not_retry_on_4xx_non_retryable(self):
        """Should NOT retry on 4xx (except 429)."""
        pass

    def test_max_attempts_respected(self):
        """Should stop after max_attempts."""
        pass

    def test_exponential_backoff(self):
        """Should use exponential backoff between retries."""
        pass

    def test_backoff_with_jitter(self):
        """Backoff should include jitter to prevent thundering herd."""
        pass

    def test_max_backoff_capped(self):
        """Backoff should be capped at max_interval."""
        pass


class TestRetryPolicy:
    """Test retry policy configuration."""

    def test_configurable_max_attempts(self):
        """max_attempts should be configurable."""
        pass

    def test_configurable_retry_on_codes(self):
        """retry_on status codes should be configurable."""
        pass

    def test_configurable_backoff_base(self):
        """Base backoff interval should be configurable."""
        pass

    def test_configurable_backoff_max(self):
        """Max backoff interval should be configurable."""
        pass
