from pydantic import BaseModel, Field, AnyUrl
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime, date


class CalendarEvent(BaseModel):
    """
    Model for creating or updating a Google Calendar event.
    """
    title: str
    start: datetime  
    end: datetime
    description: Optional[str] = None

    def to_google_format(self):
        return {
            "summary": self.title,
            "description": self.description,
            "start": {
                "dateTime": self.start.isoformat(),
                "timeZone": "UTC",  
            },
            "end": {
                "dateTime": self.end.isoformat(),
                "timeZone": "UTC",  
            },
        }

class EventFromGoogle(BaseModel):
    """
    Simple event format for frontend calendars (e.g., FullCalendar).
    """
    id: str
    title: str
    start: str  
    end: str    

class ScheduledEvent(BaseModel):
    """Represents a single calendar event extracted from the syllabus."""
    title: str = Field(..., description="The title or name of the event (e.g., 'Midterm Exam').")
    start_date: str = Field(..., description="The start date of the event in 'YYYY-MM-DD' format.")
    end_date: Optional[str] = Field(None, description="The end date of the event in 'YYYY-MM-DD' format, if applicable.")
    description: Optional[str] = Field(None, description="A brief description of the event.")

class CreateCalendarEvent(BaseModel):
    title: str
    start: datetime
    end: datetime
    description: Optional[str] = None
    location: Optional[str] = None

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



class ChatTurn(BaseModel):  
    role: Literal["user", "assistant"]
    text: str
    at: datetime

class StudyTask(BaseModel):
    title: str
    steps: List[str]
    duration_min: int  

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
    summary: Optional[str] = None                
    events: List[ScheduledEvent] = []            
    turns: List[ChatTurn] = []                    
    raw_text: Optional[str] = None

    last_flashcards: List[Flashcard] = []

class ChatRequest(BaseModel):
    session_id: str
    message: str
    keywords: Optional[List[str]] = None          

class ChatResponse(BaseModel):
    type: Literal["answer", "due_list", "study_plan", "flashcards", "summary"]
    message: str                                
    data: Optional[Dict[str, Any]] = None
