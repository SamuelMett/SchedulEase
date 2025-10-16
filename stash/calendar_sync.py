# app/calendar_sync.py
from dotenv import load_dotenv
load_dotenv() # reads env file

import os
from fastapi import HTTPException
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError

# Your public Canvas ICS link
CANVAS_ICS_URL = os.getenv(
    "CANVAS_ICS_URL",
    "https://southeastern.instructure.com/feeds/calendars/user_NH8x1NsBMLCB3DyCe45gK0PZk3IYEXl9rtpvMEBo.ics"
)

def get_canvas_ical_feed(api_url: str = None, api_key: str = None) -> str:
    """
    Returns the Canvas ICS feed URL.
    api_url and api_key are ignored for public ICS feeds.
    """
    return CANVAS_ICS_URL


def build_google_creds(token: dict) -> Credentials:
    """
    Build Google credentials safely.
    Raises Exception if refresh_token is missing.
    """
    if not token.get("refresh_token"):
        raise HTTPException(
            status_code=401,
            detail="No refresh_token found. You must re-login to Google with consent to grant offline access."
        )

    creds = Credentials(
        token=token.get("access_token"),
        refresh_token=token.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scopes=["https://www.googleapis.com/auth/calendar"]
    )
    return creds


def add_calendar_subscription(google_token: dict, ical_url: str):
    """
    Subscribes the user's Google Calendar to the provided iCal URL.
    """
    creds = build_google_creds(google_token)
    service = build("calendar", "v3", credentials=creds)

    try:
        calendar_list_entry = {"id": ical_url}
        created_calendar = service.calendarList().insert(body=calendar_list_entry).execute()
        
        # --- ADD THIS DEBUGGING LINE ---
        print("--- GOOGLE API RESPONSE ---")
        print(created_calendar)
        print("---------------------------")
        # -------------------------------
        
        return created_calendar

    except HttpError as error:
        if error.resp.status == 409:
            print("Calendar subscription already exists.")
            return {"summary": "Canvas Calendar (Already Subscribed)"}
        
        print(f"An error occurred with Google Calendar API: {error}")
        raise HTTPException(status_code=500, detail="Failed to add calendar to Google.")
