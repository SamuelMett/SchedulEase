# app/ai_processor.py
# -*- coding: utf-8 -*-

import re
import json
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

# Single shared OpenAI client
client = OpenAI()


# -------------------------------------------------
# Small heuristic: pull quick facts from raw syllabus text
# -------------------------------------------------
def _quick_fact_from_text(message: str, raw: str) -> Optional[str]:
    # very small heuristics for common facts
    if re.search(r"\binstructor|professor\b", message, re.I):
        m = re.search(r"(Instructor|Professor)\s*[:\-]\s*(.+)", raw, re.I)
        if m:
            return m.group(2).strip()
    if re.search(r"\boffice hours?\b", message, re.I):
        m = re.search(r"Office\s*Hours?\s*[:\-]\s*(.+)", raw, re.I)
        if m:
            return m.group(1).strip()
    if re.search(r"\bemail\b", message, re.I):
        m = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", raw, re.I)
        if m:
            return m.group(0)
    return None


# -------------------------------
# Existing: syllabus analysis (kept as-is)
# -------------------------------
async def extract_analysis_from_text(text: str, context_date: date) -> AiAnalysisResult | None:
    """
    Analyze syllabus text and return structured summary + dated events using a function/tool call.
    """
    system_prompt = """
You are an expert academic assistant specializing in syllabus processing. Your task is to meticulously read a course syllabus, extract a concise summary, and identify all KEY, DATE-SPECIFIC events.

**Your Guiding Rules:**
1.  **Extract Events:** Focus only on events with a specific date, such as 'Midterm Exam', 'Final Project Due', 'Assignment 1 Deadline', or 'Spring Break'.
2.  **Ignore Recurring Events:** You MUST ignore recurring, non-graded events like 'Weekly Lecture', 'Lab Section', or 'Professor's Office Hours'.
3.  **Resolve Dates:** Use the 'Relevant Academic Year' provided in the user's message to resolve all dates. If a syllabus says 'October 10th', you must combine it with the provided year to create a full 'YYYY-MM-DD' date.
4.  **Be Precise:** Event titles should be descriptive (e.g., "Homework 1 Due," not just "Homework").
5.  **Use the Tool:** You MUST return this information only by using the `extract_document_info` tool. Do not respond in plain text.
""".strip()

    user_prompt_content = f"""
Here is the context for the syllabus:
-   Current Date: {context_date.isoformat()}
-   Relevant Academic Year: {context_date.year}

Please analyze the following syllabus text based on this context.

--- START OF SYLLABUS TEXT ---
{text}
--- END OF SYLLABUS TEXT ---
""".strip()

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
# New: Study assets 
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
        '  "plan": [{"title": string, "steps": [string], "duration_min": int}],\n'
        '  "flashcards": [{"front": string, "back": string}]\n'
        "}\n\n"
        "Rules:\n"
        "- Total study time ~60-120 minutes unless the user asked differently.\n"
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


async def answer_query(message: str, ctx: ChatContext) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Answers a question using only ctx.summary and ctx.events.
    Returns (message, extra_data).
    """
    # NEW: quick facts directly from raw syllabus text (if we stored it)
    if getattr(ctx, "raw_text", None):
        qf = _quick_fact_from_text(message, ctx.raw_text or "")
        if qf:
            return qf, None

    lines: List[str] = []
    for e in (ctx.events or [])[:40]:
        lines.append(f"- {e.start_date}: {e.title}")
    events_block = "\n".join(lines) if lines else "(no dated events)"

    system = (
        "You answer only from the provided course summary and dated events. "
        "If you can't find the answer, say what is needed (e.g., 'upload a syllabus' or 'connect Canvas'). "
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
