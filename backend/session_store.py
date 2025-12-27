"""In-memory session store for anonymous chat sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, Optional
from uuid import uuid4

from coach import CoachAgent


@dataclass
class SessionRecord:
    agent: CoachAgent
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class InMemorySessionStore:
    """Holds CoachAgent instances keyed by anonymous session IDs."""

    def __init__(self, factory: Callable[[], CoachAgent], ttl_minutes: int = 60) -> None:
        self._factory = factory
        self._ttl = timedelta(minutes=ttl_minutes)
        self._sessions: Dict[str, SessionRecord] = {}

    def create(self) -> str:
        session_id = uuid4().hex
        self._sessions[session_id] = SessionRecord(agent=self._factory())
        self._cleanup()
        return session_id

    def get(self, session_id: str) -> Optional[SessionRecord]:
        record = self._sessions.get(session_id)
        if record:
            record.last_activity = datetime.now(timezone.utc)
        return record

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def _cleanup(self) -> None:
        cutoff = datetime.now(timezone.utc) - self._ttl
        expired = [key for key, record in self._sessions.items() if record.last_activity < cutoff]
        for key in expired:
            del self._sessions[key]
