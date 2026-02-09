import asyncio
from datetime import datetime, timedelta
from typing import Optional
from backend.conversation.models import ConversationSession


class InMemorySessionStore:
    def __init__(self, ttl_hours: int = 24):
        self._sessions: dict[str, ConversationSession] = {}
        self._lock = asyncio.Lock()
        self._ttl = timedelta(hours=ttl_hours)

    async def create_session(self) -> ConversationSession:
        session = ConversationSession()
        async with self._lock:
            self._sessions[session.id] = session
        return session

    async def get_session(self, session_id: str) -> Optional[ConversationSession]:
        async with self._lock:
            return self._sessions.get(session_id)

    async def update_session(self, session: ConversationSession) -> None:
        session.updated_at = datetime.utcnow()
        async with self._lock:
            self._sessions[session.id] = session

    async def delete_session(self, session_id: str) -> bool:
        async with self._lock:
            return self._sessions.pop(session_id, None) is not None

    async def list_sessions(self) -> list[ConversationSession]:
        async with self._lock:
            return list(self._sessions.values())

    async def cleanup_expired(self) -> int:
        now = datetime.utcnow()
        async with self._lock:
            expired = [sid for sid, s in self._sessions.items() if now - s.updated_at > self._ttl]
            for sid in expired:
                del self._sessions[sid]
            return len(expired)
