# app/routers/chat.py
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from ..models import (
    ChatRequest,
    ChatResponse,
    ScheduledEvent,
    AiAnalysisResult,
)
from ..memory import (
    get_ctx,
    add_turn,
    attach_analysis,
)
from ..file_reader import extract_text_from_file
from ..ai_processor import (
    extract_analysis_from_text,
    make_study_assets,
    answer_query,
)

router = APIRouter()


def _parse_event_date(d: str) -> date | None:
    try:
        return date.fromisoformat(d)
    except Exception:
        return None


def _filter_due(events: List[ScheduledEvent], days: int = 14) -> List[ScheduledEvent]:
    """Return events with start_date in [today, today+days]."""
    today = date.today()
    end = today + timedelta(days=days)
    due: List[ScheduledEvent] = []
    for ev in events or []:
        sd = _parse_event_date(ev.start_date)
        if sd and today <= sd <= end:
            due.append(ev)
    due.sort(key=lambda e: e.start_date)
    return due


def _render_due_text(events: List[ScheduledEvent]) -> str:
    if not events:
        return "No upcoming deadlines in the next two weeks."
    lines = ["Here are your upcoming deadlines:"]
    for ev in events:
        when = ev.start_date if ev.start_date else "TBD"
        lines.append(f"• {when} — {ev.title}")
    return "\n".join(lines)


# ---------- routes ----------

@router.post("/send", response_model=ChatResponse)
async def send(req: ChatRequest):
    """
    Handle a chat turn. For now:
    - "due"/"deadline"/"exam"/"test" → return due list (next 14 days)
    - "study plan"/"flashcards" → generate study assets (if syllabus attached)
    - otherwise → grounded answer from summary/events or guidance
    """
    ctx = get_ctx(req.session_id)
    add_turn(req.session_id, "user", req.message)
    msg_l = req.message.lower()

    # 1) What's due (next 14 days)
    if any(k in msg_l for k in ["what's due", "what is due", "due", "deadline", "exam", "test"]):
        upcoming = _filter_due(ctx.events, days=14)
        message = _render_due_text(upcoming)
        add_turn(req.session_id, "assistant", message)
        return ChatResponse(type="due_list", message=message, data={"due": [e.model_dump() for e in upcoming]})

    # 2) Study plan / flashcards
    if any(k in msg_l for k in ["study plan", "study", "flashcard", "review", "keywords"]) or (req.keywords):
        if not ctx.summary:
            guidance = "Upload a syllabus here or via the Import page, then ask again for a study plan."
            add_turn(req.session_id, "assistant", guidance)
            return ChatResponse(type="study_plan", message=guidance, data=None)

        assets = await make_study_assets(ctx.summary, req.keywords or [])
        msg = f"I built a {sum(t.duration_min for t in assets.plan)}-minute study plan with {len(assets.flashcards)} flashcards."
        add_turn(req.session_id, "assistant", msg)
        return ChatResponse(type="study_plan", message=msg, data=assets.model_dump())

    # 3) Grounded Q&A
    if ctx.summary or ctx.events:
        reply, extra = await answer_query(req.message, ctx)
    else:
        reply, extra = ("I don’t have a syllabus yet. Upload a PDF here or use Import.", None)

    add_turn(req.session_id, "assistant", reply)
    return ChatResponse(type="answer", message=reply, data=extra)


@router.post("/upload")
async def upload_to_session(
    session_id: str = Form(...),
    file: UploadFile = File(...),
):
    """
    In-chat upload: reuse your existing pipeline to parse the syllabus and
    attach the AiAnalysisResult to this chat session.
    """
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        # many browsers send octet-stream for PDFs; allow both
        raise HTTPException(status_code=400, detail="Please upload a PDF.")

    # Extract and analyze
    text = await extract_text_from_file(file)
    analysis: AiAnalysisResult | None = await extract_analysis_from_text(text, context_date=date.today())
    if analysis is None:
        raise HTTPException(status_code=422, detail="Could not extract structured data from this file.")

    # Store both structured and raw text in the session
    ctx = attach_analysis(session_id, analysis, raw_text=text)  # <-- raw_text passed in

    add_turn(session_id, "assistant", "Syllabus attached. You can now ask “what’s due” or request a study plan.")
    return {
        "attached_to_session": True,
        "summary": analysis.summary,
        "events_count": len(analysis.events),
    }


@router.get("/context/{session_id}")
async def get_context(session_id: str):
    """Debug endpoint to inspect what the assistant knows for this session."""
    ctx = get_ctx(session_id)
    return {
        "summary_present": bool(ctx.summary),
        "events_count": len(ctx.events or []),
        "last_turns": [t.model_dump() for t in ctx.turns[-10:]],
    }
