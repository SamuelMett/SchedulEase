# app/memory.py
from __future__ import annotations

from datetime import datetime
from typing import Dict

from .models import (
    AiAnalysisResult,
    ChatContext,
    ChatTurn,
    ScheduledEvent,
)

# In-memory store keyed by session_id
_sessions: Dict[str, ChatContext] = {}


def get_ctx(session_id: str) -> ChatContext:
    """
    Return (or create) the chat context for this session.
    Holds the latest syllabus summary, events, and chat turns.
    """
    ctx = _sessions.get(session_id)
    if ctx is None:
        ctx = ChatContext(session_id=session_id, summary=None, events=[], turns=[])
        _sessions[session_id] = ctx
    return ctx


def attach_analysis(session_id: str, analysis: AiAnalysisResult) -> ChatContext:
    """
    Save the latest syllabus analysis (summary + events) to this session.
    Returns the updated context.
    """
    ctx = get_ctx(session_id)
    ctx.summary = analysis.summary
    ctx.events = analysis.events or []
    return ctx


def add_turn(session_id: str, role: str, text: str) -> None:
    """
    Append a chat turn to the session history.
    """
    ctx = get_ctx(session_id)
    ctx.turns.append(ChatTurn(role=role, text=text, at=datetime.utcnow()))


def clear_session(session_id: str) -> None:
    """
    Optional: remove a session (useful for testing).
    """
    _sessions.pop(session_id, None)
