"""
Rate Limiting Middleware for FastAPI

Implements per-API-key rate limits using slowapi.

Rate Limit Tiers:
- Message endpoints: 500 requests/hour per API key
- Session creation: 60 sessions/hour per API key
- Health check: No limits (for monitoring)

Usage:
    from backend.middleware.rate_limit import limiter, RATE_LIMITS

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
"""

import os
import logging

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)


def get_rate_limit_key(request: Request) -> str:
    """
    Generate a rate limit key based on API key (if present) or IP address.

    This ensures rate limits are per-API-key, not per-IP, which is more
    appropriate for authenticated APIs.

    Args:
        request: FastAPI request object

    Returns:
        Rate limit key (API key hash or IP address)
    """
    # If request has been authenticated, use API key for rate limiting
    if hasattr(request.state, "api_key") and request.state.api_key:
        # Use first 12 chars of API key as identifier (enough to differentiate)
        api_key_prefix = request.state.api_key[:12] if len(request.state.api_key) >= 12 else request.state.api_key
        return f"api_key:{api_key_prefix}"

    # Fallback to IP-based limiting for unauthenticated endpoints
    return get_remote_address(request)


def get_session_count_key(request: Request) -> str:
    """
    Generate a key for tracking session count per API key.

    Args:
        request: FastAPI request object

    Returns:
        Session count tracking key
    """
    if hasattr(request.state, "api_key") and request.state.api_key:
        api_key_prefix = request.state.api_key[:12] if len(request.state.api_key) >= 12 else request.state.api_key
        return f"sessions:{api_key_prefix}"

    return f"sessions:{get_remote_address(request)}"


# Initialize rate limiter
# Using in-memory storage (simple deployment) - can be upgraded to Redis for production
limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=[]  # No default limits; specify per-endpoint
)


# Rate limit configurations (can be overridden by environment variables)
RATE_LIMITS = {
    "messages_per_hour": os.getenv("RATE_LIMIT_MESSAGES_PER_HOUR", "500"),
    "voice_concurrent": os.getenv("RATE_LIMIT_VOICE_CONCURRENT", "15"),
    "session_creation_per_hour": os.getenv("RATE_LIMIT_SESSION_CREATION_PER_HOUR", "60"),
}


# Export public API
__all__ = [
    "limiter",
    "get_rate_limit_key",
    "get_session_count_key",
    "RATE_LIMITS",
]
