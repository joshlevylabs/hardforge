"""SQLAlchemy ORM models."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Index
from backend.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False, default="")
    subscription_tier = Column(String, nullable=False, default="free")
    designs_this_month = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False, default="New Design")
    phase = Column(String, nullable=False, default="gathering")
    messages_json = Column(Text, nullable=False, default="[]")
    gathered_spec_json = Column(Text, nullable=False, default="{}")
    design_intent_json = Column(Text, nullable=True)
    feasibility_report_json = Column(Text, nullable=True)
    circuit_design_json = Column(Text, nullable=True)
    selected_topology = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_conversations_user_id", "user_id"),
    )
