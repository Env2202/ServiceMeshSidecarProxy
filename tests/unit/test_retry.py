# tests/unit/test_retry.py
# TDD: Tests written FIRST to define expected behavior

import pytest

try:
    from sidecar.pipeline.retry import RetryHandler, RetryPolicy
except ImportError:
    RetryHandler = None
    RetryPolicy = None


class TestRetryLogic:
    """Test retry behavior."""

    def test_retries_on_specified_status_codes(self):
        """Should retry on configured status codes (e.g., 5xx, 429)."""
        if RetryHandler is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/pipeline/retry.py")
        pass

    def test_retries_on_connect_failure(self):
        """Should retry on connection failure."""
        if RetryHandler is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/pipeline/retry.py")
        pass

    def test_retries_on_reset(self):
        """Should retry on connection reset."""
        if RetryHandler is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/pipeline/retry.py")
        pass

    def test_does_not_retry_on_4xx_non_retryable(self):
        """Should NOT retry on 4xx (except 429)."""
        if RetryHandler is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/pipeline/retry.py")
        pass

    def test_max_attempts_respected(self):
        """Should stop after max_attempts."""
        if RetryHandler is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/pipeline/retry.py")
        pass

    def test_exponential_backoff(self):
        """Should use exponential backoff between retries."""
        if RetryHandler is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/pipeline/retry.py")
        # base_interval=100ms, then 200ms, 400ms, ...
        pass

    def test_backoff_with_jitter(self):
        """Backoff should include jitter to prevent thundering herd."""
        if RetryHandler is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/pipeline/retry.py")
        # jitter=0.2 means ±20%
        pass

    def test_max_backoff_capped(self):
        """Backoff should be capped at max_interval."""
        if RetryHandler is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/pipeline/retry.py")
        pass


class TestRetryPolicy:
    """Test retry policy configuration."""

    def test_configurable_max_attempts(self):
        """max_attempts should be configurable."""
        if RetryPolicy is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/pipeline/retry.py")
        pass

    def test_configurable_retry_on_codes(self):
        """retry_on status codes should be configurable."""
        if RetryPolicy is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/pipeline/retry.py")
        pass

    def test_configurable_backoff_base(self):
        """Base backoff interval should be configurable."""
        if RetryPolicy is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/pipeline/retry.py")
        pass

    def test_configurable_backoff_max(self):
        """Max backoff interval should be configurable."""
        if RetryPolicy is None:
            pytest.skip("Not implemented yet - TDD: implement sidecar/pipeline/retry.py")
        pass
