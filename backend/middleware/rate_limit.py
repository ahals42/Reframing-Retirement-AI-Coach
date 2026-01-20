"""
Rate Limiting Middleware for FastAPI

This module provides rate limiting functionality using slowapi (compatible with Flask-Limiter).
Implements per-API-key rate limits for different endpoint types.

Rate Limit Tiers:
- Message endpoints: 100 requests/hour per API key
- Voice endpoints: 10 concurrent streams per API key
- Session creation: 50 active sessions per API key
- Health check: No limits (for monitoring)

Security Features:
- Per-API-key tracking (not just IP-based)
- Token usage budgets
- Concurrent request limits for streaming
- 429 Too Many Requests responses with retry-after headers

Usage:
    from backend.middleware.rate_limit import limiter, get_rate_limit_key

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.post("/sessions/{session_id}/messages")
    @limiter.limit("100/hour", key_func=get_rate_limit_key)
    async def send_message(request: Request, session_id: str):
        return {"message": "ok"}
"""

import os
import logging
from typing import Optional

from fastapi import Request, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

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
    "messages_per_hour": os.getenv("RATE_LIMIT_MESSAGES_PER_HOUR", "100"),
    "voice_concurrent": os.getenv("RATE_LIMIT_VOICE_CONCURRENT", "10"),
    "session_creation_per_hour": os.getenv("RATE_LIMIT_SESSION_CREATION_PER_HOUR", "20"),
}


def check_session_limit(request: Request, max_sessions: int = 50) -> bool:
    """
    Check if API key has exceeded maximum active sessions.

    This is a placeholder for session count tracking. In production, this should
    be implemented with a proper session store that tracks sessions per API key.

    Args:
        request: FastAPI request object
        max_sessions: Maximum allowed active sessions

    Returns:
        True if under limit, False if limit exceeded
    """
    # TODO: Implement actual session count tracking
    # This would require modifying session_store.py to track sessions per API key
    # For now, we return True (no enforcement)
    return True


def check_concurrent_streams(request: Request, max_concurrent: int = 10) -> bool:
    """
    Check if API key has exceeded maximum concurrent streams.

    This is a placeholder for concurrent stream tracking. In production, this should
    use a counter in Redis or similar to track active streaming connections.

    Args:
        request: FastAPI request object
        max_concurrent: Maximum allowed concurrent streams

    Returns:
        True if under limit, False if limit exceeded
    """
    # TODO: Implement actual concurrent stream tracking
    # This would require tracking active SSE/streaming connections
    # For now, we return True (no enforcement)
    return True


class SessionLimitExceeded(Exception):
    """Exception raised when session creation limit is exceeded."""
    pass


class ConcurrentStreamLimitExceeded(Exception):
    """Exception raised when concurrent stream limit is exceeded."""
    pass


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom handler for rate limit exceeded responses.

    Args:
        request: FastAPI request object
        exc: RateLimitExceeded exception

    Returns:
        JSONResponse with 429 status code
    """
    logger.warning(
        f"Rate limit exceeded for {request.method} {request.url.path} "
        f"from {request.client.host if request.client else 'unknown'}"
    )

    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please slow down.",
            "retry_after": getattr(exc, "retry_after", 60)
        },
        headers={
            "Retry-After": str(getattr(exc, "retry_after", 60))
        }
    )


# Token usage tracking (placeholder for cost control)
class TokenUsageTracker:
    """
    Track token usage per API key for budget enforcement.

    In production, this should use a persistent store (Redis, database)
    to track usage across application restarts and multiple instances.
    """

    def __init__(self):
        """Initialize token usage tracker."""
        self._usage = {}  # api_key -> token_count
        self._budgets = {}  # api_key -> max_tokens

    def record_usage(self, api_key: str, tokens: int):
        """
        Record token usage for an API key.

        Args:
            api_key: The API key
            tokens: Number of tokens used
        """
        if api_key not in self._usage:
            self._usage[api_key] = 0
        self._usage[api_key] += tokens

        logger.info(f"Token usage for API key {api_key[:8]}...: {self._usage[api_key]} tokens")

    def set_budget(self, api_key: str, max_tokens: int):
        """
        Set token budget for an API key.

        Args:
            api_key: The API key
            max_tokens: Maximum allowed tokens
        """
        self._budgets[api_key] = max_tokens

    def check_budget(self, api_key: str) -> bool:
        """
        Check if API key is within budget.

        Args:
            api_key: The API key

        Returns:
            True if under budget, False if exceeded
        """
        if api_key not in self._budgets:
            return True  # No budget set

        usage = self._usage.get(api_key, 0)
        budget = self._budgets[api_key]

        return usage < budget

    def get_usage(self, api_key: str) -> int:
        """
        Get current token usage for an API key.

        Args:
            api_key: The API key

        Returns:
            Total tokens used
        """
        return self._usage.get(api_key, 0)


# Global token usage tracker
token_tracker = TokenUsageTracker()


# Export public API
__all__ = [
    "limiter",
    "get_rate_limit_key",
    "get_session_count_key",
    "check_session_limit",
    "check_concurrent_streams",
    "rate_limit_exceeded_handler",
    "token_tracker",
    "RATE_LIMITS",
    "SessionLimitExceeded",
    "ConcurrentStreamLimitExceeded",
]
