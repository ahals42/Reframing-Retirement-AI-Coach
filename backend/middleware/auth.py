"""
API Key Authentication Middleware for FastAPI

This module provides API key-based authentication using the X-API-Key header.
API keys are validated against a list stored in the API_KEYS environment variable.

Security Features:
- Constant-time comparison to prevent timing attacks
- Structured logging for security events
- 401 Unauthorized responses for missing/invalid keys
- Per-API-key usage tracking support

Usage:
    from backend.middleware.auth import require_api_key

    @app.get("/protected-endpoint")
    @require_api_key
    async def protected_endpoint(request: Request):
        api_key = request.state.api_key  # Validated key available here
        return {"message": "Access granted"}
"""

import os
import logging
import secrets
from typing import Optional, List
from functools import wraps

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class APIKeyAuth:
    """Manages API key authentication and validation."""

    def __init__(self):
        """Initialize API key authentication from environment variables."""
        self._valid_keys: List[str] = self._load_api_keys()
        if not self._valid_keys:
            logger.warning(
                "No API keys configured in API_KEYS environment variable. "
                "All authenticated endpoints will reject requests."
            )

    def _load_api_keys(self) -> List[str]:
        """
        Load API keys from environment variable.

        Returns:
            List of valid API keys (empty list if not configured)
        """
        keys_str = os.getenv("API_KEYS", "")
        if not keys_str:
            return []

        # Split by comma and strip whitespace
        keys = [key.strip() for key in keys_str.split(",") if key.strip()]
        logger.info(f"Loaded {len(keys)} API keys from environment")
        return keys

    def validate_key(self, provided_key: Optional[str]) -> bool:
        """
        Validate an API key using constant-time comparison.

        Args:
            provided_key: The API key to validate (from X-API-Key header)

        Returns:
            True if key is valid, False otherwise
        """
        if not provided_key or not self._valid_keys:
            return False

        # Use constant-time comparison to prevent timing attacks
        # Check against all valid keys
        for valid_key in self._valid_keys:
            if secrets.compare_digest(provided_key, valid_key):
                return True

        return False

    def get_api_key_from_request(self, request: Request) -> Optional[str]:
        """
        Extract API key from request headers.

        Args:
            request: FastAPI request object

        Returns:
            API key string or None if not present
        """
        # Check X-API-Key header (standard)
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return api_key

        # Fallback: check Authorization header with Bearer scheme
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix

        return None


# Global instance
_auth = APIKeyAuth()


def require_api_key(func):
    """
    Decorator to require API key authentication on FastAPI endpoints.

    This decorator:
    1. Extracts the API key from the X-API-Key header
    2. Validates the key against configured keys
    3. Returns 401 Unauthorized if key is missing or invalid
    4. Attaches the validated key to request.state.api_key for downstream use

    Usage:
        @app.post("/sessions")
        @require_api_key
        async def create_session(request: Request):
            # request.state.api_key contains validated key
            return {"session_id": "..."}

    Args:
        func: The FastAPI route handler function

    Returns:
        Wrapped function with authentication enforcement
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract request object from kwargs (FastAPI dependency injection)
        request: Optional[Request] = kwargs.get("request")

        # If request not in kwargs, try to find it in args
        if not request:
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

        if not request:
            logger.error("require_api_key decorator used on endpoint without Request parameter")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

        # Extract API key from request
        provided_key = _auth.get_api_key_from_request(request)

        if not provided_key:
            logger.warning(
                f"Authentication failed: Missing API key for {request.method} {request.url.path} "
                f"from {request.client.host if request.client else 'unknown'}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing API key. Provide X-API-Key header.",
                headers={"WWW-Authenticate": "ApiKey"},
            )

        # Validate API key
        if not _auth.validate_key(provided_key):
            logger.warning(
                f"Authentication failed: Invalid API key for {request.method} {request.url.path} "
                f"from {request.client.host if request.client else 'unknown'}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )

        # Store validated API key in request state for downstream use
        request.state.api_key = provided_key

        # Log successful authentication
        logger.info(
            f"Authentication successful for {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )

        # Call the actual endpoint handler
        return await func(*args, **kwargs)

    return wrapper


# Export public API
__all__ = ["require_api_key", "APIKeyAuth"]
