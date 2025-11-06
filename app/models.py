from pydantic import BaseModel, Field, AnyUrl
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime, date

# ----------------------------
# Calendar / Events (original)
# ----------------------------

class CalendarEvent(BaseModel):
    """
    Model for creating or updating a Google Calendar event.
    """
    title: str
    start: datetime  # FastAPI will parse ISO 8601 strings
    end: datetime
    description: Optional[str] = None

    # Convert to the format Google's API expects.
    def to_google_format(self):
        return {
            "summary": self.title,
            "description": self.description,
            "start": {
                "dateTime": self.start.isoformat(),
                "timeZone": "UTC",  # Or derive this from the datetime
            },
            "end": {
                "dateTime": self.end.isoformat(),
                "timeZone": "UTC",  # Or derive this from the datetime
            },
        }

class EventFromGoogle(BaseModel):
    """
    Simple event format for frontend calendars (e.g., FullCalendar).
    """
    id: str
    title: str
    start: str  # ISO string
    end: str    # ISO string

class ScheduledEvent(BaseModel):
    """Represents a single calendar event extracted from the syllabus."""
    title: str = Field(..., description="The title or name of the event (e.g., 'Midterm Exam').")
    start_date: str = Field(..., description="The start date of the event in 'YYYY-MM-DD' format.")
    end_date: Optional[str] = Field(None, description="The end date of the event in 'YYYY-MM-DD' format, if applicable.")
    description: Optional[str] = Field(None, description="A brief description of the event.")

class AiAnalysisResult(BaseModel):
    """Structured data extracted from the syllabus by the AI."""
    summary: str = Field(..., description="A concise summary of the course syllabus.")
    events: List[ScheduledEvent] = Field(..., description="A list of all scheduled events found in the syllabus.")

class FinalApiResponse(BaseModel):
    source_file_name: str
    summary: str
    scheduled_events: List[ScheduledEvent]

class EventFromSelector(BaseModel):
    """Represents a new event created with a date selector."""
    title: str = Field(..., description="The title for the new event.")
    selected_date: date = Field(..., description="The date chosen from the date selector.")
    description: Optional[str] = Field(None, description="An optional description for the event.")

class Course(BaseModel):
    id: int
    name: str

class CalendarSubscription(BaseModel):
    """Model for subscribing to an external .ics calendar url."""
    url: AnyUrl = Field(..., description="The full URL of the .ics calendar to subscribe to.")


# ---------------------------------
# Chat / Study-plan models (new)
# ---------------------------------

class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    text: str
    at: datetime

class StudyTask(BaseModel):
    title: str
    steps: List[str]
    duration_min: int  # minutes per block

class Flashcard(BaseModel):
    front: str
    back: str

class StudyAssets(BaseModel):
    """Structured output for study planning & quick review."""
    keywords: List[str] = []
    plan: List[StudyTask] = []
    flashcards: List[Flashcard] = []

class ChatContext(BaseModel):
    """
    What the assistant knows for a given session.
    """
    session_id: str
    summary: Optional[str] = None                 # syllabus summary text
    events: List[ScheduledEvent] = []             # upcoming dated items
    turns: List[ChatTurn] = []                    # last few chat turns
    raw_text: Optional[str] = None                # full syllabus text (for quick facts)

class ChatRequest(BaseModel):
    session_id: str
    message: str
    keywords: Optional[List[str]] = None          # optional hint for study-plan generation

class ChatResponse(BaseModel):
    # "type" helps the UI render specific UIs (due list, plan, flashcards)
    type: Literal["answer", "due_list", "study_plan", "flashcards"]
    message: str                                  # concise text for the chat bubble
    data: Optional[Dict[str, Any]] = None         # structured payload when applicable
