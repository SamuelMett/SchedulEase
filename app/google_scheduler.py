import httpx
from datetime import date, timedelta
from authlib.integrations.starlette_client import OAuth

from .models import ScheduledEvent

async def schedule_event_on_google_calendar(
    event: ScheduledEvent,
    token: dict,
    oauth: OAuth
) -> bool:
    """
    Schedules a single event on the user's primary Google Calendar.

    Args:
        event: The ScheduledEvent object with event details.
        token: The user's OAuth token dictionary from the session.
        oauth: The Authlib OAuth instance.

    Returns:
        True if successful, False otherwise.
    """
    api_url = 'https://www.googleapis.com/calendar/v3/calendars/primary/events'

    try:
        # Google's API for all-day events requires the end date to be exclusive.
        # So, an event on "2025-10-15" must have an end date of "2025-10-16".
        start_dt = date.fromisoformat(event.start_date)
        end_dt = date.fromisoformat(event.end_date or event.start_date)
        exclusive_end_dt = end_dt + timedelta(days=1)

        event_data = {
            'summary': event.title,
            'description': event.description or f"Event from syllabus: {event.title}",
            'start': {
                'date': start_dt.isoformat(),
            },
            'end': {
                'date': exclusive_end_dt.isoformat(),
            },
        }

        # Make the authenticated API call to create the event
        resp = await oauth.google.post(api_url, json=event_data, token=token)
        resp.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)

        print(f"✅ Successfully scheduled event: '{event.title}'")
        return True

    except httpx.HTTPStatusError as e:
        print(f"❌ Error scheduling event '{event.title}': {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ An unexpected error occurred while scheduling '{event.title}': {e}")
        return False