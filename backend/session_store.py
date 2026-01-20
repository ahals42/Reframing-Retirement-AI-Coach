"""In-memory session store for anonymous chat sessions with security limits."""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, Optional
from uuid import uuid4

from coach import CoachAgent

logger = logging.getLogger(__name__)

# Security constants
MAX_TOTAL_SESSIONS = int(os.getenv("MAX_TOTAL_SESSIONS", "1000"))  # Global limit
MAX_SESSIONS_PER_API_KEY = int(os.getenv("MAX_SESSIONS_PER_API_KEY", "50"))  # Per-key limit


@dataclass
class SessionRecord:
    """
    Session record with agent instance and metadata.

    Attributes:
        agent: CoachAgent instance for this session
        created_at: Session creation timestamp
        last_activity: Last activity timestamp (for TTL)
        api_key_hash: Hash of API key that created this session (for tracking)
        message_count: Number of messages in this session (for limits)
    """
    agent: CoachAgent
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    api_key_hash: Optional[str] = None  # First 8 chars of API key
    message_count: int = 0


class InMemorySessionStore:
    """
    Holds CoachAgent instances keyed by anonymous session IDs.

    Security features:
    - TTL-based session expiration
    - Global session limit (prevents memory exhaustion)
    - Per-API-key session limits
    - Session count tracking
    - Memory monitoring
    """

    def __init__(self, factory: Callable[[], CoachAgent], ttl_minutes: int = 60) -> None:
        self._factory = factory
        self._ttl = timedelta(minutes=ttl_minutes)
        self._sessions: Dict[str, SessionRecord] = {}
        logger.info(f"Initialized session store with TTL={ttl_minutes} minutes")

    def create(self, api_key_hash: Optional[str] = None) -> str:
        """
        Create a new session.

        Args:
            api_key_hash: First 8 chars of API key (for tracking)

        Returns:
            Session ID

        Raises:
            RuntimeError: If session limits are exceeded
        """
        # Clean up expired sessions first
        self._cleanup()

        # Check global session limit
        if len(self._sessions) >= MAX_TOTAL_SESSIONS:
            logger.error(
                f"Global session limit exceeded: {len(self._sessions)}/{MAX_TOTAL_SESSIONS}"
            )
            raise RuntimeError(
                f"Server capacity exceeded. Maximum {MAX_TOTAL_SESSIONS} active sessions allowed."
            )

        # Check per-API-key limit
        if api_key_hash:
            api_key_session_count = sum(
                1 for record in self._sessions.values()
                if record.api_key_hash == api_key_hash
            )
            if api_key_session_count >= MAX_SESSIONS_PER_API_KEY:
                logger.warning(
                    f"API key {api_key_hash}... exceeded session limit: "
                    f"{api_key_session_count}/{MAX_SESSIONS_PER_API_KEY}"
                )
                raise RuntimeError(
                    f"Maximum {MAX_SESSIONS_PER_API_KEY} sessions per API key exceeded. "
                    f"Delete unused sessions first."
                )

        # Create session
        session_id = uuid4().hex
        self._sessions[session_id] = SessionRecord(
            agent=self._factory(),
            api_key_hash=api_key_hash
        )

        logger.info(
            f"Created session {session_id} "
            f"(total: {len(self._sessions)}, "
            f"api_key: {api_key_hash or 'none'})"
        )

        return session_id

    def get(self, session_id: str) -> Optional[SessionRecord]:
        """
        Get session record and update last activity.

        Args:
            session_id: Session identifier

        Returns:
            SessionRecord or None if not found
        """
        record = self._sessions.get(session_id)
        if record:
            record.last_activity = datetime.now(timezone.utc)
            record.message_count += 1
        return record

    def delete(self, session_id: str) -> None:
        """
        Delete a session.

        Args:
            session_id: Session identifier
        """
        record = self._sessions.pop(session_id, None)
        if record:
            logger.info(
                f"Deleted session {session_id} "
                f"(total: {len(self._sessions)}, "
                f"messages: {record.message_count})"
            )

    def get_stats(self) -> Dict[str, int]:
        """
        Get session store statistics.

        Returns:
            Dictionary with session counts
        """
        return {
            "total_sessions": len(self._sessions),
            "max_sessions": MAX_TOTAL_SESSIONS,
            "max_per_api_key": MAX_SESSIONS_PER_API_KEY,
        }

    def _cleanup(self) -> None:
        """Remove expired sessions based on TTL."""
        cutoff = datetime.now(timezone.utc) - self._ttl
        expired = [
            key for key, record in self._sessions.items()
            if record.last_activity < cutoff
        ]

        if expired:
            for key in expired:
                del self._sessions[key]
            logger.info(f"Cleaned up {len(expired)} expired sessions")
