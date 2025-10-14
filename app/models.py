from pydantic import BaseModel, Field
from typing import List, Optional
import datetime

# --- AI Extraction Model ---
# This defines the structure we want the AI to fill for us.

class PotentialEvent(BaseModel):
    title: str = Field(..., description="A concise title for the calendar event.")
    description: str = Field(..., description="A short description of the event, including the source text.")
    start_datetime_utc: str = Field(..., description="The event's start time in ISO 8601 UTC format.")
    end_datetime_utc: str = Field(..., description="The event's end time in ISO 8601 UTC format.")
    is_all_day: bool = Field(..., description="True if the event does not have a specific time.")

class AiAnalysisResult(BaseModel):
    summary: str = Field(..., description="A concise summary of the entire document's purpose.")
    events: List[PotentialEvent] = Field(..., description="A list of all calendar events found in the document.")


# --- API Response Models ---
# These define the final JSON response from our API endpoint.

class ScheduledEvent(BaseModel):
    canvas_event_id: int
    title: str
    start_at: str
    end_at: str
    html_url: str

class FinalApiResponse(BaseModel):
    source_file_name: str
    summary: str
    scheduled_events: List[ScheduledEvent]