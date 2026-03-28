# sidecar/pipeline/rate_limit.py - Rate limiting
# Implements token bucket rate limiting per plan

from typing import Dict, Optional
import time
from dataclasses import dataclass

from ..telemetry.logging import get_logger

logger = get_logger("rate_limiter")


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    limit: int = 100  # requests per window
    window: float = 1.0  # window in seconds
    burst: int = 0  # burst allowance (0 = limit)


class TokenBucket:
    """Token bucket for rate limiting."""

    def __init__(self, rate: int, burst: int):
        self.rate = rate  # tokens per second
        self.burst = burst
        self.tokens = burst
        self.last_refill = time.time()

    def _refill(self):
        """Refill tokens based on time elapsed."""
        now = time.time()
        time_passed = now - self.last_refill
        tokens_to_add = time_passed * self.rate

        self.tokens = min(self.burst, self.tokens + tokens_to_add)
        self.last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens. Returns True if successful."""
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class RateLimiter:
    """Rate limiter using token buckets per key."""

    def __init__(self, rate: int = 100, burst: int = 200):
        self.default_rate = rate
        self.default_burst = burst
        self.buckets: Dict[str, TokenBucket] = {}

    def allow(self, key: str = "global", rate: Optional[int] = None, burst: Optional[int] = None) -> bool:
        """Check if request is allowed for this key."""
        if key not in self.buckets:
            r = rate or self.default_rate
            b = burst or self.default_burst
            self.buckets[key] = TokenBucket(r, b)

        allowed = self.buckets[key].consume(1)

        if not allowed:
            logger.warning(
                "Rate limit exceeded",
                key=key,
                rate=rate or self.default_rate
            )
        else:
            logger.debug(
                "Request allowed",
                key=key,
                remaining_tokens=self.buckets[key].tokens
            )

        return allowed

    def reset(self, key: str = None):
        """Reset rate limiter for a key or all keys."""
        if key is None:
            self.buckets.clear()
        elif key in self.buckets:
            del self.buckets[key]


class TokenBucketRateLimiter(RateLimiter):
    """Token bucket rate limiter with per-client and global limits."""

    def __init__(self, rate: int = 100, burst: int = 200):
        super().__init__(rate, burst)

    async def allow_request(self, client_key: str = "global") -> bool:
        """Check if request from client is allowed."""
        # Check global limit first
        if not self.allow("global"):
            return False

        # Then check per-client limit
        return self.allow(client_key)

