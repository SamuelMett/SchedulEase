from __future__ import annotations

import re
from datetime import date, timedelta, datetime
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request

from ..models import ChatRequest, ChatResponse, ScheduledEvent, AiAnalysisResult, EventFromGoogle
from ..memory import get_ctx, add_turn, attach_analysis
from ..file_reader import extract_text_from_file
from ..ai_processor import (
    extract_analysis_from_text,
    make_study_assets,
    answer_query,
    general_chat,
)

from ..calendar_api import get_events_for_range, get_token

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



async def _get_calendar_events_range(request: Request, days: int) -> List[EventFromGoogle]:
    """
    Fetch events from Google Calendar for the next `days` days.
    """
    start_dt = datetime.utcnow()
    end_dt = start_dt + timedelta(days=days)
    token = get_token(request)
    return await get_events_for_range(
        request=request,
        start=start_dt,
        end=end_dt,
        token=token,
    )


async def _get_calendar_events_between(request: Request, start: date, end: date) -> List[EventFromGoogle]:
    """
    Fetch events from Google Calendar between two calendar dates (inclusive).
    """
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.max.time())
    token = get_token(request)
    return await get_events_for_range(
        request=request,
        start=start_dt,
        end=end_dt,
        token=token,
    )


def _google_date_from_string(s: str) -> date | None:
    """
    Google returns either 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SSZ'.
    This converts both forms into a date object.
    """
    if not s:
        return None
    try:
        pure = s.split("T", 1)[0]
        return date.fromisoformat(pure)
    except Exception:
        return None


def _pretty_google_date(s: str) -> str:
    d = _google_date_from_string(s)
    if not d:
        return s
    return d.strftime("%B %d, %Y")



_MONTH_LOOKUP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def _extract_month_day(text: str) -> date | None:
    """
    Find patterns like 'dec 5', 'december 5th', etc. and return a date
    (using the current year).
    """
    m = re.search(
        r"\b("
        r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
        r"aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
        r")\s+(\d{1,2})(st|nd|rd|th)?\b",
        text,
        re.I,
    )
    if not m:
        return None

    month_name = m.group(1).lower()
    day_str = m.group(2)
    try:
        day = int(day_str)
    except ValueError:
        return None

    # normalize month key
    if month_name in _MONTH_LOOKUP:
        month = _MONTH_LOOKUP[month_name]
    else:
        month = _MONTH_LOOKUP.get(month_name[:3], None)
    if not month:
        return None

    year = date.today().year
    try:
        return date(year, month, day)
    except ValueError:
        return None



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
async def send(req: ChatRequest, request: Request):
    ctx = get_ctx(req.session_id)
    add_turn(req.session_id, "user", req.message)
    msg_l = req.message.lower()

    exam_line = _find_assessment_date(msg_l, ctx.events or [])
    if exam_line:
        add_turn(req.session_id, "assistant", exam_line)
        return ChatResponse(type="answer", message=exam_line, data=None)

    if "final exam" in msg_l and ("when" in msg_l or "what day" in msg_l or "date" in msg_l):
        events = await _get_calendar_events_range(request, days=180)
        matches = [
            e for e in events
            if re.search(r"final exam", (e.title or ""), re.I)
        ]
        if matches:
            first = matches[0]
            date_str = _pretty_google_date(first.start)
            message = f"Your final exam on Google Calendar is on {date_str}: {first.title}."
        else:
            message = "I couldn't find a 'Final Exam' event on your Google Calendar."
        add_turn(req.session_id, "assistant", message)
        return ChatResponse(type="answer", message=message, data=None)

    target_date = _extract_month_day(msg_l)
    if target_date:
        events = await _get_calendar_events_between(request, target_date, target_date)
        if not events:
            date_label = target_date.strftime("%B %d, %Y")
            message = f"I don't see any events on your Google Calendar for {date_label}."
        else:
            exams = [
                e for e in events
                if re.search(r"\b(exam|test|quiz)\b", (e.title or ""), re.I)
            ]
            chosen = exams[0] if exams else events[0]
            date_label = target_date.strftime("%B %d, %Y")
            message = f"On {date_label} you have: {chosen.title}."
        add_turn(req.session_id, "assistant", message)
        return ChatResponse(type="answer", message=message, data=None)

    # --- Google Calendar: relative ranges ---

    if "next week" in msg_l or "coming week" in msg_l:
        events = await _get_calendar_events_range(request, days=7)
        if not events:
            message = "You have no events scheduled for next week on your Google Calendar."
        else:
            message = "Here’s what’s coming up next week from your Google Calendar:\n" + "\n".join(
                f"• {_pretty_google_date(e.start)} — {e.title}" for e in events
            )
        add_turn(req.session_id, "assistant", message)
        return ChatResponse(type="answer", message=message, data=None)

    if "tomorrow" in msg_l:
        tomorrow = date.today() + timedelta(days=1)
        events = await _get_calendar_events_between(request, tomorrow, tomorrow)
        if not events:
            message = "You have nothing due tomorrow on your Google Calendar."
        else:
            message = "Here’s what’s due tomorrow from your Google Calendar:\n" + "\n".join(
                f"• {_pretty_google_date(e.start)} — {e.title}" for e in events
            )
        add_turn(req.session_id, "assistant", message)
        return ChatResponse(type="answer", message=message, data=None)

    if "this month" in msg_l or "rest of this month" in msg_l:
        today = date.today()
        next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
        end_of_month = next_month - timedelta(days=1)
        events = await _get_calendar_events_between(request, today, end_of_month)
        if not events:
            message = "You have no events scheduled for the rest of this month on your Google Calendar."
        else:
            message = "Here’s what’s happening this month from your Google Calendar:\n" + "\n".join(
                f"• {_pretty_google_date(e.start)} — {e.title}" for e in events
            )
        add_turn(req.session_id, "assistant", message)
        return ChatResponse(type="answer", message=message, data=None)

    if any(k in msg_l for k in ["what's due", "what is due", "due soon", "due soon?", "due", "deadline", "upcoming"]):
        # 1) syllabus-based events (from uploaded syllabi)
        syl_upcoming = _filter_due(ctx.events, days=14)

        # 2) Google Calendar events in next 14 days
        try:
            today = date.today()
            end = today + timedelta(days=14)
            gcal_all = await _get_calendar_events_between(request, today, end)
        except Exception:
            gcal_all = []

        DUE_PATTERN = r"(exam|quiz|test|assignment|project|homework|paper|report|midterm|final|due)"
        gcal_upcoming = [
            e for e in gcal_all
            if re.search(DUE_PATTERN, (e.title or ""), re.I)
        ]

        if not syl_upcoming and not gcal_upcoming:
            message = "No upcoming deadlines in the next two weeks."
            add_turn(req.session_id, "assistant", message)
            return ChatResponse(
                type="due_list",
                message=message,
                data={"due": []},
            )

        lines: List[str] = ["Here’s what’s due soon:\n"]

        if syl_upcoming:
            lines.append("📘 From your uploaded syllabi:")
            for ev in syl_upcoming:
                lines.append(f"• {ev.start_date or 'TBD'} — {ev.title}")
            lines.append("")

        if gcal_upcoming:
            lines.append("📅 From your Google Calendar:")
            for e in gcal_upcoming:
                lines.append(f"• {_pretty_google_date(e.start)} — {e.title}")

        message = "\n".join(lines)
        add_turn(req.session_id, "assistant", message)
        return ChatResponse(
            type="due_list",
            message=message,
            data={
                "due_syllabus": [e.model_dump() for e in syl_upcoming],
                "due_gcal": [e.model_dump() for e in gcal_upcoming],
            },
        )

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

    if ctx.summary or ctx.events:
        reply, extra = await answer_query(req.message, ctx)
        add_turn(req.session_id, "assistant", reply)
        return ChatResponse(type="answer", message=reply, data=extra)

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
