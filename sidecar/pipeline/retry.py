# sidecar/pipeline/retry.py - Retry handler
# Uses tenacity for retry logic per plan

from typing import Optional, List, Callable, Any
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError
import functools


class RetryPolicy:
    """Retry policy configuration."""

    def __init__(
        self,
        max_attempts: int = 3,
        retry_on: List[str] = None,
        base_interval: float = 0.1,
        max_interval: float = 10.0,
        jitter: float = 0.2
    ):
        self.max_attempts = max_attempts
        self.retry_on = retry_on or ["5xx", "connect_failure", "reset"]
        self.base_interval = base_interval
        self.max_interval = max_interval
        self.jitter = jitter

    def should_retry(self, exception: Exception, status_code: Optional[int] = None) -> bool:
        """Determine if request should be retried."""
        if status_code and status_code >= 500:
            return "5xx" in self.retry_on
        if status_code == 429:
            return True
        if isinstance(exception, ConnectionError):
            return "connect_failure" in self.retry_on
        if isinstance(exception, asyncio.TimeoutError):
            return True
        return False


class RetryHandler:
    """Handles retries with backoff for HTTP requests."""

    def __init__(self, policy: Optional[RetryPolicy] = None):
        self.policy = policy or RetryPolicy()

    def get_retry_decorator(self):
        """Get tenacity retry decorator based on policy."""
        return retry(
            stop=stop_after_attempt(self.policy.max_attempts),
            wait=wait_exponential(
                multiplier=self.policy.base_interval,
                max=self.policy.max_interval
            ),
            retry=retry_if_exception_type((Exception,)),
            reraise=True
        )

    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic."""
        retry_decorator = self.get_retry_decorator()

        @retry_decorator
        async def _wrapped():
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Check if we should retry
                if self.policy.should_retry(e):
                    raise  # Let tenacity handle retry
                else:
                    raise  # Don't retry

        return await _wrapped()

    def should_retry_on_status(self, status_code: int) -> bool:
        """Check if status code should trigger retry."""
        if status_code >= 500:
            return "5xx" in self.policy.retry_on
        if status_code == 429:
            return True
        return False

