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
    # instructor / professor
    if re.search(r"\binstructor|professor\b", message, re.I):
        m = re.search(r"(?:Instructor|Professor)\s*[:\-]\s*(.+)", raw, re.I)
        if m:
            return m.group(1).strip()
    # office hours
    if re.search(r"\boffice hours?\b", message, re.I):
        m = re.search(r"Office\s*Hours?\s*[:\-]\s*(.+)", raw, re.I)
        if m:
            return m.group(1).strip()
    # email
    if re.search(r"\bemail\b", message, re.I):
        m = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", raw, re.I)
        if m:
            return m.group(0)
    return None
# --------------------------------------------------------


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
    Answer using ctx.summary and ctx.events; first try raw_text quick facts.
    """
    if getattr(ctx, "raw_text", None):
        hit = _quick_fact_from_text(message, ctx.raw_text or "")
        if hit:
            return hit, {"source": "raw_text"}

    lines: List[str] = []
    for e in (ctx.events or [])[:40]:
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
