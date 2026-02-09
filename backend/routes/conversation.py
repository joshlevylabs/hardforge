"""Conversation routes — multi-turn design agent."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from backend.conversation.models import (
    ConversationPhase,
    ConversationSummary,
    Message,
    SendMessageRequest,
    SendMessageResponse,
)
from backend.conversation.orchestrator import Orchestrator

router = APIRouter()


def _get_orchestrator(request: Request) -> Orchestrator:
    store = request.app.state.session_store
    return Orchestrator(store)


@router.post("/conversations", response_model=SendMessageResponse)
async def create_conversation(
    request: Request,
    body: Optional[SendMessageRequest] = None,
):
    """Create a new conversation session, optionally with an initial message."""
    orchestrator = _get_orchestrator(request)
    session = await orchestrator.session_store.create_session()

    if body and body.content:
        response_msg = await orchestrator.handle_message(session, body.content)
    else:
        # Welcome message
        welcome = Message(
            role="assistant",
            content="Hi! I'm your HardForge design assistant. Tell me about the hardware project you'd like to build — what kind of circuit are you looking for?",
        )
        session.messages.append(welcome)
        await orchestrator.session_store.update_session(session)
        response_msg = welcome

    return SendMessageResponse(
        message=response_msg,
        phase=session.phase,
        gathered_spec=session.gathered_spec,
        circuit_design=session.circuit_design,
    )


@router.post("/conversations/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(
    session_id: str,
    body: SendMessageRequest,
    request: Request,
):
    """Send a message to an existing conversation."""
    orchestrator = _get_orchestrator(request)
    session = await orchestrator.session_store.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Conversation not found")

    response_msg = await orchestrator.handle_message(session, body.content)

    return SendMessageResponse(
        message=response_msg,
        phase=session.phase,
        gathered_spec=session.gathered_spec,
        circuit_design=session.circuit_design,
    )


@router.get("/conversations/{session_id}")
async def get_conversation(session_id: str, request: Request):
    """Get full conversation state."""
    store = request.app.state.session_store
    session = await store.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return session.model_dump()


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations(request: Request):
    """List all active conversations."""
    store = request.app.state.session_store
    sessions = await store.list_sessions()

    return [
        ConversationSummary(
            id=s.id,
            phase=s.phase,
            message_count=len(s.messages),
            project_type=s.gathered_spec.project_type,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sessions
    ]


@router.delete("/conversations/{session_id}")
async def delete_conversation(session_id: str, request: Request):
    """Delete a conversation."""
    store = request.app.state.session_store
    deleted = await store.delete_session(session_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"status": "deleted"}
