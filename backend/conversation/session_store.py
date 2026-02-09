import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional
from backend.conversation.models import ConversationSession, GatheredSpec, Message


class InMemorySessionStore:
    def __init__(self, ttl_hours: int = 24):
        self._sessions: dict[str, ConversationSession] = {}
        self._lock = asyncio.Lock()
        self._ttl = timedelta(hours=ttl_hours)

    async def create_session(self, user_id: Optional[str] = None) -> ConversationSession:
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

    async def list_sessions(self, user_id: Optional[str] = None) -> list[ConversationSession]:
        async with self._lock:
            return list(self._sessions.values())

    async def cleanup_expired(self) -> int:
        now = datetime.utcnow()
        async with self._lock:
            expired = [sid for sid, s in self._sessions.items() if now - s.updated_at > self._ttl]
            for sid in expired:
                del self._sessions[sid]
            return len(expired)


class SQLiteSessionStore:
    """Persistent session store backed by SQLite via SQLAlchemy."""

    def __init__(self):
        from backend.database import SessionLocal
        self._session_factory = SessionLocal

    def _derive_name(self, spec: GatheredSpec) -> str:
        parts = []
        if spec.project_type:
            parts.append(spec.project_type.replace("_", " ").title())
        if spec.driver and spec.driver.get("model"):
            parts.append(spec.driver["model"])
        return " — ".join(parts) if parts else "New Design"

    def _to_pydantic(self, row) -> ConversationSession:
        """Convert ORM Conversation row to Pydantic ConversationSession."""
        messages_data = json.loads(row.messages_json) if row.messages_json else []
        messages = [Message(**m) for m in messages_data]

        spec_data = json.loads(row.gathered_spec_json) if row.gathered_spec_json else {}
        gathered_spec = GatheredSpec(**spec_data) if spec_data else GatheredSpec()

        return ConversationSession(
            id=row.id,
            phase=row.phase,
            messages=messages,
            gathered_spec=gathered_spec,
            design_intent=json.loads(row.design_intent_json) if row.design_intent_json else None,
            feasibility_report=json.loads(row.feasibility_report_json) if row.feasibility_report_json else None,
            circuit_design=json.loads(row.circuit_design_json) if row.circuit_design_json else None,
            selected_topology=row.selected_topology,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def create_session(self, user_id: Optional[str] = None) -> ConversationSession:
        from backend.models_db import Conversation
        session = ConversationSession()
        db = self._session_factory()
        try:
            row = Conversation(
                id=session.id,
                user_id=user_id or "",
                name="New Design",
                phase=session.phase.value,
                messages_json="[]",
                gathered_spec_json=session.gathered_spec.model_dump_json(),
            )
            db.add(row)
            db.commit()
        finally:
            db.close()
        return session

    async def get_session(self, session_id: str) -> Optional[ConversationSession]:
        from backend.models_db import Conversation
        db = self._session_factory()
        try:
            row = db.query(Conversation).filter(Conversation.id == session_id).first()
            if not row:
                return None
            return self._to_pydantic(row)
        finally:
            db.close()

    async def update_session(self, session: ConversationSession) -> None:
        from backend.models_db import Conversation
        db = self._session_factory()
        try:
            row = db.query(Conversation).filter(Conversation.id == session.id).first()
            if not row:
                return
            row.phase = session.phase.value if hasattr(session.phase, 'value') else session.phase
            row.messages_json = json.dumps([m.model_dump(mode="json") for m in session.messages])
            row.gathered_spec_json = session.gathered_spec.model_dump_json()
            row.design_intent_json = json.dumps(session.design_intent) if session.design_intent else None
            row.feasibility_report_json = json.dumps(session.feasibility_report) if session.feasibility_report else None
            row.circuit_design_json = json.dumps(session.circuit_design) if session.circuit_design else None
            row.selected_topology = session.selected_topology
            row.name = self._derive_name(session.gathered_spec)
            row.updated_at = datetime.utcnow()
            db.commit()
        finally:
            db.close()

    async def delete_session(self, session_id: str) -> bool:
        from backend.models_db import Conversation
        db = self._session_factory()
        try:
            row = db.query(Conversation).filter(Conversation.id == session_id).first()
            if not row:
                return False
            db.delete(row)
            db.commit()
            return True
        finally:
            db.close()

    async def list_sessions(self, user_id: Optional[str] = None) -> list[ConversationSession]:
        from backend.models_db import Conversation
        db = self._session_factory()
        try:
            query = db.query(Conversation)
            if user_id:
                query = query.filter(Conversation.user_id == user_id)
            rows = query.order_by(Conversation.updated_at.desc()).all()
            return [self._to_pydantic(r) for r in rows]
        finally:
            db.close()
