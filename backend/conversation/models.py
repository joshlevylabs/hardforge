from __future__ import annotations
from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class ConversationPhase(str, Enum):
    GATHERING = "gathering"
    CLARIFYING = "clarifying"
    CONFIRMING = "confirming"
    DESIGNING = "designing"
    REVIEWING = "reviewing"
    COMPLETE = "complete"


class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[dict] = None


class GatheredSpec(BaseModel):
    """Accumulated specifications from conversation."""
    project_type: Optional[str] = None
    driver: Optional[dict] = None  # {manufacturer, model, ts_params}
    target_specs: dict = Field(default_factory=dict)
    constraints: dict = Field(default_factory=dict)
    firmware_requirements: Optional[str] = None
    additional_notes: list[str] = Field(default_factory=list)


class ConversationSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    phase: ConversationPhase = ConversationPhase.GATHERING
    messages: list[Message] = Field(default_factory=list)
    gathered_spec: GatheredSpec = Field(default_factory=GatheredSpec)
    design_intent: Optional[dict] = None
    feasibility_report: Optional[dict] = None
    circuit_design: Optional[dict] = None
    selected_topology: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=50000)


class SendMessageResponse(BaseModel):
    session_id: str
    message: Message
    phase: ConversationPhase
    gathered_spec: Optional[GatheredSpec] = None
    circuit_design: Optional[dict] = None


class ConversationSummary(BaseModel):
    id: str
    phase: ConversationPhase
    message_count: int
    project_type: Optional[str] = None
    name: str = "New Design"
    created_at: datetime
    updated_at: datetime
