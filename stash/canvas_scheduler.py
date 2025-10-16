# app/canvas_scheduler.py

from canvasapi import Canvas
from .models import PotentialEvent, ScheduledEvent

def schedule_event_in_canvas(api_url: str, api_key: str, course_id: int, event_data: PotentialEvent) -> ScheduledEvent | None:
    try:
        canvas = Canvas(api_url, api_key)
        
        # --- THIS IS THE FIX ---
        # 1. Get the current user object associated with the API key.
        user = canvas.get_current_user()

        # 2. Set the context_code to the user's calendar, not the course's.
        #    The course_id is now just for context in the description.
        event_payload = {
            'context_code': f'user_{user.id}', 
            'title': event_data.title,
            'start_at': event_data.start_datetime_utc,
            'end_at': event_data.end_datetime_utc,
            'description': f"(From Course ID: {course_id}) {event_data.description}"
        }
        # ------------------------
        
        # Create the event on the main canvas object
        new_event = canvas.create_calendar_event(calendar_event=event_payload)
        
        return ScheduledEvent(
            canvas_event_id=new_event.id,
            title=new_event.title,
            start_at=str(new_event.start_at),
            end_at=str(new_event.end_at),
            html_url=new_event.html_url
        )
    except Exception as e:
        print(f"Error creating Canvas event '{event_data.title}': {e}")
        return None