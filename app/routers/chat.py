from __future__ import annotations

import re
from datetime import date, timedelta
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from ..models import ChatRequest, ChatResponse, ScheduledEvent, AiAnalysisResult
from ..memory import get_ctx, add_turn, attach_analysis
from ..file_reader import extract_text_from_file
from ..ai_processor import (
    extract_analysis_from_text,
    make_study_assets,
    answer_query,
    general_chat,
)

router = APIRouter()

def _parse_event_date(d: str) -> date | None:
    try:
        return date.fromisoformat(d)
    except Exception:
        return None

def _filter_due(events: List[ScheduledEvent], days: int = 14) -> List[ScheduledEvent]:
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
        lines.append(f"• {ev.start_date or 'TBD'} — {ev.title}")
    return "\n".join(lines)

# ----- exam/test/quiz N -----
_ORD = {
    "1": 1, "one": 1, "first": 1,
    "2": 2, "two": 2, "second": 2,
    "3": 3, "three": 3, "third": 3,
    "4": 4, "four": 4, "fourth": 4,
    "5": 5, "five": 5, "fifth": 5,
}
def _find_number(s: str) -> int | None:
    for token, n in _ORD.items():
        if re.search(rf"\b{token}\b", s, re.I):
            return n
    return None

def _find_assessment_date(message: str, events: List[ScheduledEvent]) -> str | None:
    n = _find_number(message)
    if n is None:
        return None
    filtered = [e for e in events or [] if re.search(r"\b(exam|test|quiz)\b", e.title, re.I)]
    filtered.sort(key=lambda e: (e.start_date, e.title))
    idx = n - 1
    if 0 <= idx < len(filtered):
        tgt = filtered[idx]
        return f"{tgt.title} is on {tgt.start_date}."
    return None

def _format_study_assets_text(assets) -> str:
    total = sum(t.duration_min for t in (assets.plan or []))
    lines = [f"I built a {total}-minute study plan with {len(assets.flashcards)} flashcards.", "", "Plan:"]
    for t in assets.plan[:4]:
        lines.append(f"• {t.title} — {t.duration_min} min")
        for s in t.steps[:3]:
            lines.append(f"   - {s}")
    if len(assets.plan) > 4:
        lines.append(f"... and {len(assets.plan) - 4} more blocks.")
    if assets.flashcards:
        lines += ["", "Flashcards (first 3):"]
        for fc in assets.flashcards[:3]:
            lines.append(f"Q: {fc.front}  -  A: {fc.back}")
    return "\n".join(lines)

@router.post("/send", response_model=ChatResponse)
async def send(req: ChatRequest):
    ctx = get_ctx(req.session_id)
    add_turn(req.session_id, "user", req.message)
    msg_l = req.message.lower()

    # exam/test/quiz N
    exam_line = _find_assessment_date(msg_l, ctx.events or [])
    if exam_line:
        add_turn(req.session_id, "assistant", exam_line)
        return ChatResponse(type="answer", message=exam_line, data=None)

    # due list
    if any(k in msg_l for k in ["what's due", "what is due", "due", "deadline"]):
        upcoming = _filter_due(ctx.events, days=14)
        message = _render_due_text(upcoming)
        add_turn(req.session_id, "assistant", message)
        return ChatResponse(type="due_list", message=message, data={"due": [e.model_dump() for e in upcoming]})

    # study plan / flashcards
    if any(k in msg_l for k in ["study plan", "study", "flashcard", "review", "keywords"]) or (req.keywords):
        if not ctx.summary:
            guidance = "Upload a syllabus here or via the Import page, then ask again for a study plan."
            add_turn(req.session_id, "assistant", guidance)
            return ChatResponse(type="study_plan", message=guidance, data=None)

        assets = await make_study_assets(ctx.summary, req.keywords or [])
        pretty = _format_study_assets_text(assets)
        add_turn(req.session_id, "assistant", pretty)
        return ChatResponse(type="study_plan", message=pretty, data=assets.model_dump())

    # grounded Q&A
    if ctx.summary or ctx.events:
        reply, extra = await answer_query(req.message, ctx)
        add_turn(req.session_id, "assistant", reply)
        return ChatResponse(type="answer", message=reply, data=extra)

    # general GPT fallback
    general = await general_chat(req.message)
    add_turn(req.session_id, "assistant", general)
    return ChatResponse(type="answer", message=general, data=None)

@router.post("/upload")
async def upload_to_session(session_id: str = Form(...), file: UploadFile = File(...)):
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="Please upload a PDF.")

    text = await extract_text_from_file(file)
    analysis: AiAnalysisResult | None = await extract_analysis_from_text(text, context_date=date.today())
    if analysis is None:
        raise HTTPException(status_code=422, detail="Could not extract structured data from this file.")

    # store structured + raw text for quick facts
    attach_analysis(session_id, analysis, raw_text=text)
    add_turn(session_id, "assistant", "Syllabus attached. You can now ask 'what's due' or request a study plan.")
    return {"attached_to_session": True, "summary": analysis.summary, "events_count": len(analysis.events)}

@router.get("/context/{session_id}")
async def get_context(session_id: str):
    ctx = get_ctx(session_id)
    return {
        "summary_present": bool(ctx.summary),
        "events_count": len(ctx.events or []),
        "last_turns": [t.model_dump() for t in ctx.turns[-10:]],
    }
