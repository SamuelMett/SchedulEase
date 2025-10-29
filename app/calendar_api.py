# In a new file: app/calendar_api.py

from fastapi import APIRouter, Request, HTTPException, Depends, UploadFile, File
from authlib.integrations.starlette_client import OAuth
from typing import List
from datetime import datetime
from .models import CalendarEvent, EventFromGoogle, CalendarSubscription
import httpx
from ics import Calendar

# We'll need to pass the `oauth` object to this router
# Or, better, create a dependency to get the token
def get_token(request: Request):
    """Dependency to get the auth token from the session."""
    token = request.session.get('token')
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return token

# Import your new models
from .models import CalendarEvent, EventFromGoogle

# Helper to get the actual `oauth.google` object
# You'll need to pass this in from main.py
def get_oauth_client(request: Request) -> OAuth:
    return request.app.state.oauth

# This is our new router
router = APIRouter(
    prefix="/api/calendar",  # All routes here will start with /api/calendar
    tags=["Calendar API"]    # For the /docs page
)

### --- The 4 CRUD Endpoints --- ###

# 1. READ (Get events for a date range)
@router.get("/events", response_model=List[EventFromGoogle])
async def get_events_for_range(
    request: Request,
    start: datetime,  # Query param: /events?start=...&end=...
    end: datetime,
    token: dict = Depends(get_token)
):
    """
    Fetch events from Google Calendar for a specific date range.
    """
    oauth = request.app.state.oauth
    
    params = {
        "timeMin": start.isoformat() + "Z", # 'Z' for UTC
        "timeMax": end.isoformat() + "Z",
        "orderBy": "startTime",
        "singleEvents": True
    }

    try:
        resp = await oauth.google.get(
            'https://www.googleapis.com/calendar/v3/calendars/primary/events',
            token=token,
            params=params
        )
        resp.raise_for_status()
        data = resp.json()
        
        # Convert Google's format to our simple EventFromGoogle format
        events = []
        for event in data.get('items', []):
            start_info = event.get('start', {})
            end_info = event.get('end', {})
            
            # Handle all-day vs. specific-time events
            start_time = start_info.get('dateTime', start_info.get('date'))
            end_time = end_info.get('dateTime', end_info.get('date'))

            events.append(EventFromGoogle(
                id=event.get('id'),
                title=event.get('summary', 'No Title'),
                start=start_time,
                end=end_time
            ))
        return events

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not fetch calendar events: {e}")


# 2. CREATE (Add a new event)
@router.post("/events", response_model=EventFromGoogle)
async def create_new_event(
    event: CalendarEvent, # Gets data from request body
    request: Request,
    token: dict = Depends(get_token)
):
    """
    Create a new event in Google Calendar.
    """
    oauth = request.app.state.oauth
    
    try:
        resp = await oauth.google.post(
            'https://www.googleapis.com/calendar/v3/calendars/primary/events',
            token=token,
            json=event.to_google_format() # Use our Pydantic helper
        )
        resp.raise_for_status()
        data = resp.json()
        
        # Return the new event in our simple format
        start_info = data.get('start', {})
        end_info = data.get('end', {})
        return EventFromGoogle(
            id=data.get('id'),
            title=data.get('summary', 'No Title'),
            start=start_info.get('dateTime', start_info.get('date')),
            end=end_info.get('dateTime', end_info.get('date'))
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not create event: {e}")


# 3. UPDATE (Change an existing event)
@router.put("/events/{event_id}", response_model=EventFromGoogle)
async def update_existing_event(
    event_id: str,
    event: CalendarEvent, # Gets data from request body
    request: Request,
    token: dict = Depends(get_token)
):
    """
    Update an existing event in Google Calendar (e.g., drag-and-drop).
    """
    oauth = request.app.state.oauth
    
    try:
        url = f'https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}'
        resp = await oauth.google.put(
            url,
            token=token,
            json=event.to_google_format() # Use our Pydantic helper
        )
        resp.raise_for_status()
        data = resp.json()
        
        # Return the updated event
        start_info = data.get('start', {})
        end_info = data.get('end', {})
        return EventFromGoogle(
            id=data.get('id'),
            title=data.get('summary', 'No Title'),
            start=start_info.get('dateTime', start_info.get('date')),
            end=end_info.get('dateTime', end_info.get('date'))
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not update event: {e}")


# 4. DELETE (Remove an event)
@router.delete("/events/{event_id}", status_code=204)
async def delete_existing_event(
    event_id: str,
    request: Request,
    token: dict = Depends(get_token)
):
    """
    Delete an event from Google Calendar.
    """
    oauth = request.app.state.oauth
    
    try:
        url = f'https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}'
        resp = await oauth.google.delete(url, token=token)
        resp.raise_for_status()
        
        # 204 No Content is the standard response for a successful delete
        return
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not delete event: {e}")

@router.post("/subscribe", status_code=202)
async def subscribe_to_calendar(
    subscription: CalendarSubscription,
    request: Request,
    token: dict = Depends(get_token)
):
    """
    Subscribes Google Calendar to an external .ics URL.
    This provides live syncing.
    """
    oauth = request.app.state.oauth
    api_url = 'https://www.googleapis.com/calendar/v3/users/me/calendarList'
    
    calendar_resource = {
        'id': str(subscription.url), # The ID for a subscription is the URL itself
        'selected': True
    }

    try:
        resp = await oauth.google.post(
            api_url,
            token=token,
            json=calendar_resource
        )
        resp.raise_for_status()
        
        return {"status": "subscription_added", "calendar_id": resp.json().get('id')}
        
    except Exception as e:
        # This is the key error the frontend will check for
        if hasattr(e, 'response') and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Google could not find a valid calendar at that URL.")
        if hasattr(e, 'response') and e.response.status_code == 409:
            raise HTTPException(status_code=409, detail="You are already subscribed to this calendar.")
        
        print(f"Error subscribing to calendar: {e}")
        raise HTTPException(status_code=500, detail="Could not subscribe to calendar.")
    
# ---
# Endpoint 2: The "Import from URL" Fallback
# ---
@router.post("/import-ics", status_code=200)
async def import_from_ics(
    subscription: CalendarSubscription,
    request: Request,
    token: dict = Depends(get_token)
):
    """
    Fetches an .ics URL (as a proxy), parses it, and adds the events
    one-by-one. This is a ONE-TIME import, not a subscription.
    """
    oauth = request.app.state.oauth
    
    # 1. Fetch the .ics file using a friendly user-agent
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36"
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                str(subscription.url), 
                headers=headers, 
                follow_redirects=True,
                timeout=10.0
            )
            resp.raise_for_status()
            ics_data = resp.text
            
    except httpx.RequestError as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch calendar. The URL may be invalid or the server is down: {e}")

    # 2. Parse the file and add to Google
    try:
        cal = Calendar(ics_data)
        imported_count, failed_count = await _import_events_to_google(cal, oauth, token)
        return {
            "status": "import_complete",
            "imported_count": imported_count,
            "failed_count": failed_count
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse calendar data or import events: {e}")
    
# ---
# Endpoint 3: The "Import from File Upload"
# ---
@router.post("/upload-ics", status_code=200)
async def upload_and_import_ics(
    request: Request,
    token: dict = Depends(get_token),
    file: UploadFile = File(...)
):
    """
    Accepts an uploaded .ics file, parses it, and adds the events
    one-by-one. This is a ONE-TIME import.
    """
    oauth = request.app.state.oauth

    # 1. Read the file content
    try:
        ics_data = (await file.read()).decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read file: {e}")

    # 2. Parse the file and add to Google
    try:
        cal = Calendar(ics_data)
        imported_count, failed_count = await _import_events_to_google(cal, oauth, token)
        return {
            "status": "upload_complete",
            "imported_count": imported_count,
            "failed_count": failed_count,
            "source_file_name": file.filename
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse calendar data or import events: {e}")

# ---
# Refactored Helper Function (to avoid code duplication)
# ---
async def _import_events_to_google(cal: Calendar, oauth: OAuth, token: dict) -> (int, int):
    """Helper function to loop through .ics events and add them to Google."""
    imported_count = 0
    failed_count = 0
    google_api_url = 'https://www.googleapis.com/calendar/v3/calendars/primary/events'

    for event in cal.events:
        # We need a start and end time to create an event
        if not event.begin or not event.end:
            continue

        try:
            # Convert to our Pydantic model to use its helper
            pydantic_event = CalendarEvent(
                title=event.name or "No Title",
                start=event.begin.datetime,
                end=event.end.datetime,
                description=event.description or None
            )
            
            # Call Google's API to create the event
            await oauth.google.post(
                google_api_url,
                token=token,
                json=pydantic_event.to_google_format()
            )
            imported_count += 1
            
        except Exception as e:
            # Catch errors (like validation or API) and continue
            print(f"Failed to import event '{event.name}': {e}")
            failed_count += 1
            
    return (imported_count, failed_count)