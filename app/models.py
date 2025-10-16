from pydantic import BaseModel, Field
from typing import List, Optional
import datetime

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

class Course(BaseModel):
    id: int
    name: str