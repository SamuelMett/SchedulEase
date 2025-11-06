# app/memory.py
from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from .models import ChatContext, ChatTurn, AiAnalysisResult

# Very simple in-memory store (OK for dev)
_CONTEXTS: Dict[str, ChatContext] = {}


def get_ctx(session_id: str) -> ChatContext:
    """Fetch or create a chat context for this session."""
    ctx = _CONTEXTS.get(session_id)
    if ctx is None:
        ctx = ChatContext(
            session_id=session_id,
            summary=None,
            events=[],
            turns=[],
            raw_text=None,
        )
        _CONTEXTS[session_id] = ctx
    return ctx


def add_turn(session_id: str, role: str, text: str) -> ChatContext:
    """Append a chat turn to the context."""
    ctx = get_ctx(session_id)
    ctx.turns.append(ChatTurn(role=role, text=text, at=datetime.now()))
    return ctx


def attach_analysis(
    session_id: str,
    analysis: AiAnalysisResult,
    raw_text: Optional[str] = None,
) -> ChatContext:
    """
    Attach parsed syllabus info to the session.
    Optionally store full raw syllabus text for quick fact lookups.
    """
    ctx = get_ctx(session_id)
    ctx.summary = analysis.summary
    ctx.events = analysis.events
    if raw_text is not None:
        ctx.raw_text = raw_text
    return ctx
