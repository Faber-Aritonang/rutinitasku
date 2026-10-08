"""
Tests for Rate Limiter
"""

import pytest
import time
from unittest.mock import patch

from config import RateLimiter


def test_rate_limiter_allows_requests():
    """Test rate limiter allows requests under limit."""
    limiter = RateLimiter(max_requests=5, window_seconds=60)

    for _ in range(5):
        assert limiter.is_allowed() is True


def test_rate_limiter_blocks_excess():
    """Test rate limiter blocks requests over limit."""
    limiter = RateLimiter(max_requests=3, window_seconds=60)

    # Use up the limit
    for _ in range(3):
        assert limiter.is_allowed() is True

    # Next request should be blocked
    assert limiter.is_allowed() is False


def test_rate_limiter_window_expiry():
    """Test rate limiter allows requests after window expires."""
    limiter = RateLimiter(max_requests=2, window_seconds=1)

    # Use up the limit
    limiter.is_allowed()
    limiter.is_allowed()
    assert limiter.is_allowed() is False

    # Wait for window to expire
    time.sleep(1.1)

    # Should be allowed again
    assert limiter.is_allowed() is True


def test_rate_limiter_wait_time():
    """Test wait time calculation."""
    limiter = RateLimiter(max_requests=1, window_seconds=10)

    limiter.is_allowed()

    wait_time = limiter.get_wait_time()
    assert 0 < wait_time <= 10


def test_rate_limiter_no_wait_when_available():
    """Test no wait time when requests available."""
    limiter = RateLimiter(max_requests=5, window_seconds=60)

    assert limiter.get_wait_time() == 0.0


def test_rate_limiter_default_values():
    """Test default rate limiter values."""
    limiter = RateLimiter()

    assert limiter.max_requests == 30
    assert limiter.window_seconds == 60