# -*- coding: utf-8 -*-

import json
import re
from typing import List, Optional, Tuple, Dict, Any
from datetime import date
from openai import OpenAI

from .models import (
    AiAnalysisResult,
    StudyAssets,
    StudyTask,
    Flashcard,
    ChatContext,
)

client = OpenAI()

# ---------- quick facts from raw syllabus text ----------
def _quick_fact_from_text(message: str, raw: str) -> Optional[str]:
    """
    Very small regex helpers to pull common fields directly from the raw syllabus text.
    Tries instructor, email, office hours, meeting schedule, and location.
    """
    msg = message.lower()

    # Instructor / Professor
    if re.search(r"\binstructor|professor\b", msg):
        m = re.search(r"(?:Instructor|Professor)\s*[:\-]\s*(.+)", raw, re.I)
        if m:
            return m.group(1).strip()

    # Email
    if re.search(r"\bemail\b", msg):
        m = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", raw, re.I)
        if m:
            return m.group(0)

    # Office hours
    if re.search(r"\boffice hours?\b", msg):
        m = re.search(r"Office\s*Hours?\s*[:\-]\s*(.+)", raw, re.I)
        if m:
            return m.group(1).strip()

    # Class meeting schedule (e.g., "Tuesdays & Thursdays 2:00 PM - 4:00 PM")
    if re.search(r"\b(when|what time|meet|meeting)\b", msg):
        m = re.search(
            r"(?:Class\s*(?:Meets|Meeting(?:s)?)|Lecture|Class\s*Time)\s*[:\-]\s*(.+)",
            raw,
            re.I,
        )
        if m:
            return m.group(1).strip()

    # Class location / room
    if re.search(r"\b(where|location|room|building|class located)\b", msg):
        m = re.search(r"(?:Location|Room)\s*[:\-]\s*([^\n]+)", raw, re.I)
        if m:
            return m.group(1).strip()
        # sometimes embedded in schedule lines: "... (Room 214, Science Building)"
        m2 = re.search(r"\((Room[^)]+)\)", raw, re.I)
        if m2:
            return m2.group(1).strip()

    return None
# --------------------------------------------------------


# -------------------------------
# simple event matching helpers
# -------------------------------
def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()

def _number_tokens(s: str) -> List[str]:
    return re.findall(r"\d+", s)

def _find_event_by_query(message: str, events) -> Optional[Dict[str, str]]:
    """
    Deterministically match questions like:
      - "When is exam 3?"
      - "When is Assignment 1 due?"
      - "When is the Final Project Report due?"
      - "When is the first day of class?"
    Returns {"title": ..., "date": ...} or None.
    """
    q = _normalize(message)
    nums = set(_number_tokens(q))

    labels: List[str] = []
    if "assignment" in q or "homework" in q or "hw" in q:
        labels.append("assignment")
    if "quiz" in q:
        labels.append("quiz")
    if "exam" in q or "test" in q or "midterm" in q:
        labels.extend(["exam", "test", "midterm"])
    if "final project" in q or "project report" in q or "final report" in q:
        labels.extend(["final project", "project report", "report"])
    if "first day" in q or "classes begin" in q or "start of class" in q:
        labels.extend(["first day", "classes begin", "start of classes"])

    best = None
    best_score = -1

    for e in (events or []):
        title_n = _normalize(e.title)
        score = 0

        # label hits
        for lab in labels:
            if lab in title_n:
                score += 2

        # number hits (e.g., "2" in "Quiz 2")
        if nums:
            tnums = set(_number_tokens(title_n))
            if nums & tnums:
                score += 2

        # generic cues
        if "when" in q or "due" in q or "date" in q:
            score += 1

        if any(k in title_n for k in ["assignment", "quiz", "exam", "test", "final", "project", "report", "first day", "classes"]):
            score += 1

        if score > best_score:
            best_score = score
            best = e

    if best and best_score >= 2 and best.start_date:
        return {"title": best.title, "date": best.start_date}

    # special fallback just for "first day"
    if any(k in q for k in ["first day", "classes begin", "start of classes"]):
        for e in (events or []):
            t = _normalize(e.title)
            if ("first" in t or "begin" in t) and e.start_date:
                return {"title": e.title, "date": e.start_date}

    return None


# -------------------------------
# Existing: syllabus analysis
# -------------------------------
async def extract_analysis_from_text(text: str, context_date: date) -> AiAnalysisResult | None:
    """
    Analyze syllabus text and return structured summary + dated events using a function/tool call.
    """
    system_prompt = (
        "You are an expert academic assistant specializing in syllabus processing. "
        "Your task is to meticulously read a course syllabus, extract a concise summary, "
        "and identify all KEY, DATE-SPECIFIC events.\n\n"
        "Guiding Rules:\n"
        "1) Extract Events: focus only on items with a specific date (e.g., Midterm Exam, Final Project Due).\n"
        "2) Ignore recurring, non-graded items (weekly lecture, office hours, etc.).\n"
        "3) Resolve Dates: use the provided Relevant Academic Year to form YYYY-MM-DD dates.\n"
        "4) Be precise and descriptive in event titles.\n"
        "5) You must return via the extract_document_info tool only."
    )

    user_prompt_content = (
        f"Context:\n"
        f"- Current Date: {context_date.isoformat()}\n"
        f"- Relevant Academic Year: {context_date.year}\n\n"
        f"Please analyze the following syllabus text based on this context.\n\n"
        f"--- START OF SYLLABUS TEXT ---\n"
        f"{text}\n"
        f"--- END OF SYLLABUS TEXT ---\n"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_content},
            ],
            tools=[{
                "type": "function",
                "function": {
                    "name": "extract_document_info",
                    "description": "Extract summary and events from the document.",
                    "parameters": AiAnalysisResult.model_json_schema(),
                },
            }],
            tool_choice={"type": "function", "function": {"name": "extract_document_info"}},
        )

        response_message = response.choices[0].message

        if response_message.tool_calls:
            tool_call = response_message.tool_calls[0]
            result_data = json.loads(tool_call.function.arguments)
            return AiAnalysisResult(**result_data)
        else:
            print("--- AI did not use the tool. Response content: ---")
            print(response_message.content)
            print("-------------------------------------------------")
            return None

    except Exception as e:
        print(f"Error calling OpenAI or processing its response: {e}")
        return None


# -------------------------------
# Study assets (plan + flashcards)
# -------------------------------
async def make_study_assets(syllabus_text: str, keywords: List[str]) -> StudyAssets:
    """
    Builds a compact study plan and flashcards using OpenAI.
    Returns structured StudyAssets.
    """
    prompt = (
        "You are a teaching assistant. Given a course syllabus text and optional target keywords, "
        "produce a compact study plan and flashcards.\n\n"
        "Output strictly as JSON with this shape:\n"
        "{\n"
        '  "keywords": [string],\n'
        '  "plan": [{"title": "string", "steps": ["string"], "duration_min": 30}],\n'
        '  "flashcards": [{"front": "string", "back": "string"}]\n'
        "}\n\n"
        "Rules:\n"
        "- Total study time about 60-120 minutes unless the user asked differently.\n"
        "- Steps are concrete actions (read, outline, test, review).\n"
        "- Flashcards: crisp, factual, one concept per card.\n"
    )

    user = (
        f"SYLLABUS:\n{syllabus_text}\n\n"
        f"TARGET_KEYWORDS: {', '.join(keywords) if keywords else '(none)'}"
    )

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )
    raw = resp.choices[0].message.content
    data = json.loads(raw)

    plan = [
        StudyTask(
            title=item.get("title", "Study Block"),
            steps=item.get("steps", []),
            duration_min=int(item.get("duration_min", 30)),
        )
        for item in data.get("plan", [])
    ]
    flashcards = [
        Flashcard(front=fc.get("front", ""), back=fc.get("back", ""))
        for fc in data.get("flashcards", [])
    ]
    return StudyAssets(
        keywords=data.get("keywords", keywords or []),
        plan=plan,
        flashcards=flashcards,
    )


# -------------------------------
# Grounded Q&A
# -------------------------------
async def answer_query(message: str, ctx: ChatContext) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Answer using (1) raw_text quick facts, then (2) deterministic event lookup,
    then (3) list logic for deadlines (all/upcoming/past), else (4) a grounded
    LLM fallback over summary + events.
    """
    # 1) quick facts from raw syllabus text
    if getattr(ctx, "raw_text", None):
        hit = _quick_fact_from_text(message, ctx.raw_text or "")
        if hit:
            return hit, {"source": "raw_text"}

    # 2) try deterministic event match (Assignment/Quiz/Exam N, Final Project, First day)
    ev = _find_event_by_query(message, ctx.events or [])
    if ev:
        reply = f"{ev['title']} is on {ev['date']}."
        return reply, {"match": ev}

    # 3) explicit deadline listing logic (all / upcoming / past)
    q = message.lower()
    events = ctx.events or []

    def _to_date(s: Optional[str]) -> Optional[date]:
        try:
            return date.fromisoformat(s) if s else None
        except Exception:
            return None

    # sort all events by date (None at the end)
    events_sorted = sorted(
        events,
        key=lambda e: (_to_date(e.start_date) is None, _to_date(e.start_date) or date.max)
    )

    mentions_deadlines = any(
        k in q for k in [
            "deadline", "deadlines", "due", "due dates", "assignments", "assignment",
            "quiz", "quizzes", "exam", "exams", "test", "tests", "project", "report", "milestone"
        ]
    )

    wants_all = ("all" in q) or ("everything" in q) or ("full" in q)
    wants_upcoming = any(k in q for k in ["upcoming", "next", "future"])
    wants_past = "past" in q

    if mentions_deadlines or wants_upcoming or wants_all or wants_past:
        today = date.today()

        def _is_future(e) -> bool:
            d = _to_date(e.start_date)
            return (d is not None) and (d >= today)

        def _is_past(e) -> bool:
            d = _to_date(e.start_date)
            return (d is not None) and (d < today)

        if wants_upcoming:
            filtered = [e for e in events_sorted if _is_future(e)]
            header = "Here are your upcoming deadlines:"
        elif wants_past:
            filtered = [e for e in events_sorted if _is_past(e)]
            header = "Here are your past deadlines:"
        else:
            # default for "deadlines/due dates" when not specifying upcoming/past → show ALL
            filtered = events_sorted
            header = "Here are all deadlines:"

        if not filtered:
            return ("No deadlines found for that request.", {"events": []})

        lines = [header]
        for e in filtered:
            when = e.start_date or "TBD"
            lines.append(f"• {when} — {e.title}")

        return ("\n".join(lines), {
            "events": [e.model_dump() for e in filtered],
            "mode": "upcoming" if wants_upcoming else ("past" if wants_past else "all")
        })

    # 4) grounded LLM fallback using summary + events (kept compact)
    lines: List[str] = []
    for e in events_sorted[:60]:
        lines.append(f"- {e.start_date}: {e.title}")
    events_block = "\n".join(lines) if lines else "(no dated events)"

    system = (
        "Answer only from the provided course summary and dated events. "
        "If not answerable, say briefly what is needed (e.g., upload a syllabus or connect Canvas). "
        "Keep replies to 1-3 sentences."
    )

    user = (
        f"SUMMARY:\n{ctx.summary or '(none)'}\n\n"
        f"EVENTS:\n{events_block}\n\n"
        f"QUESTION: {message}"
    )

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )
    answer = resp.choices[0].message.content.strip()
    return answer, None


# -------------------------------
# General GPT fallback
# -------------------------------
async def general_chat(message: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Be helpful, concise, and accurate."},
            {"role": "user", "content": message},
        ],
        temperature=0.4,
    )
    return resp.choices[0].message.content.strip()
