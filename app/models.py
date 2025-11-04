from pydantic import BaseModel, Field, AnyUrl
from typing import List, Optional
from datetime import datetime, date

class CalendarEvent(BaseModel):
    """
    Model for creating or updating a Google Calendar event.
    """
    title: str
    start: datetime  # FastAPI will parse ISO 8601 strings
    end: datetime
    description: Optional[str] = None
    
    # This helper function will convert our simple model
    # into the format Google's API expects.
    def to_google_format(self):
        return {
            'summary': self.title,
            'description': self.description,
            'start': {
                'dateTime': self.start.isoformat(),
                'timeZone': 'UTC', # Or derive this from the datetime
            },
            'end': {
                'dateTime': self.end.isoformat(),
                'timeZone': 'UTC', # Or derive this from the datetime
            },
        }

class EventFromGoogle(BaseModel):
    """
    Model to parse and return the simple event format
    that frontend calendars love (e.g., FullCalendar).
    """
    id: str
    title: str
    start: str  # Send as ISO string
    end: str    # Send as ISO string

class ScheduledEvent(BaseModel):
    """Represents a single calendar event extracted from the syllabus."""
    title: str = Field(..., description="The title or name of the event (e.g., 'Midterm Exam').")
    start_date: str = Field(..., description="The start date of the event in 'YYYY-MM-DD' format.")
    end_date: Optional[str] = Field(None, description="The end date of the event in 'YYYY-MM-DD' format, if applicable.")
    description: Optional[str] = Field(None, description="A brief description of the event.")

class AiAnalysisResult(BaseModel):
    """The structured data extracted from the syllabus by the AI."""
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

class CalendarEvent(BaseModel):
    """Model for creating or updating a Google Calendar event."""
    title: str
    start: datetime
    end: datetime
    description: Optional[str] = None
    
    def to_google_format(self):
        return {
            'summary': self.title,
            'description': self.description,
            'start': {'dateTime': self.start.isoformat(), 'timeZone': 'UTC'},
            'end': {'dateTime': self.end.isoformat(), 'timeZone': 'UTC'},
        }