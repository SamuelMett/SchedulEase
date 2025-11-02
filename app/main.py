# app/main.py
from app import calendar_api
from dotenv import load_dotenv
# load env file
load_dotenv()

from fastapi.middleware.cors import CORSMiddleware

import os
import uvicorn

from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from typing import List

from fastapi.responses import JSONResponse
from datetime import datetime, timezone, date

from .models import AiAnalysisResult
from .ai_processor import extract_analysis_from_text
from .file_reader import extract_text_from_file
from .models import ScheduledEvent, EventFromSelector
from .google_scheduler import schedule_event_on_google_calendar, schedule_multiple_events
from datetime import datetime, timezone

# --- Initialize FastAPI App ---
app = FastAPI(title="SchedulEase API")



app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:7070",  # Example: default Blazor port
        # Add the specific URL your Radzen app runs on
    ],
    allow_credentials=True,  # <-- This is ESSENTIAL for cookies
    allow_methods=["*"],     # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],     # Allow all headers
)



# --- Middleware ---
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY"),
    session_cookie="session",  # Name of the cookie
    same_site="lax",           # CSRF protection
    https_only=False           # Set to True in production
)

oauth = OAuth()
app.state.oauth = oauth

# Register the Google OAuth client
oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
client_kwargs={
        'scope': 'openid email profile https://www.googleapis.com/auth/calendar'
    },
    access_type='offline',
    prompt='consent'
)

# --- API Routes ---
app.include_router(calendar_api.router)

@app.get('/', response_class=HTMLResponse)
async def homepage(request: Request):
    """
    Displays the homepage. If the user is logged in, it shows their name and a logout link.
    Otherwise, it shows a login link.
    """
    user = request.session.get('user')
    if user:
        name = user.get('name')
        return f'''
            <h1>Hello, {name}!</h1>
            <p>You are logged in.</p>
            <a href="/profile">View Profile</a><br>
            <a href="/calendar/events">View Your Google Calendar Events</a><br>
            <a href="/logout">Logout</a>
        '''
    return '<h1>Welcome!</h1><a href="/login">Login with Google</a>'

@app.get('/login')
async def login(request: Request):
    """
    Redirects the user to Google's authentication page.
    The redirect_uri must match the one configured in the Google Cloud Console.
    """
    redirect_uri = "http://127.0.0.1:8000/auth"
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get('/auth')
async def auth(request: Request):
    """
    This is the callback route that Google redirects to after authentication.
    It processes the authorization token and stores user info in the session.
    """
    try:
        token = await oauth.google.authorize_access_token(request)
        
    except Exception as e:
        # If there's an error, this will print it to your console
        print(f"Error during authorize_access_token: {e}")
        return HTMLResponse(f"<h1>Error logging in: {e}</h1>")
    
    user_info = token.get('userinfo')

    if user_info:
        request.session['user'] = dict(user_info)
    
    request.session['token'] = token

    return RedirectResponse(url='/')

@app.get('/logout')
async def logout(request: Request):
    """
    Clears the user session and redirects to the homepage.
    """
    request.session.clear()
    return RedirectResponse(url='/')

@app.get('/profile', response_class=HTMLResponse)
async def profile(request: Request):
    """
    A protected route that displays user profile information from the session.
    """
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url='/login')

    return f"""
        <h1>Profile</h1>
        <p><strong>Name:</strong> {user.get('name')}</p>
        <p><strong>Email:</strong> {user.get('email')}</p>
        <img src="{user.get('picture')}" alt="Profile Picture">
        <br><br>
        <a href="/">Home</a>
    """

@app.get('/calendar/events')
async def calendar_events(request: Request):
    token = request.session.get('token')
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        # Get the first day of the current year.
        current_year = datetime.now().year
        start_of_year = datetime(current_year, 1, 1, tzinfo=timezone.utc)
        time_min_param = start_of_year.isoformat()

        params = {
            "timeMin": time_min_param,
            "orderBy": "startTime",
            "singleEvents": True
        }

        resp = await oauth.google.get(
            'https://www.googleapis.com/calendar/v3/calendars/primary/events',
            token=token,
            params=params
        )
        resp.raise_for_status()
        data = resp.json()
        
        # Convert events to JSON suitable for frontend calendar
        events = []
        for event in data.get('items', []):
            start_info = event.get('start', {})
            end_info = event.get('end', {})

            start_time = start_info.get('dateTime', start_info.get('date'))
            end_time = end_info.get('dateTime', end_info.get('date'))

            events.append({
                "title": event.get('summary', 'No Title'),
                "start": start_time,
                "end": end_time
            })

        return JSONResponse(content=events)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not fetch calendar events: {e}")

@app.post("/upload-syllabus", response_model=AiAnalysisResult)
async def upload_and_analyze_syllabus(file: UploadFile = File(...)):
    """
    Accepts a syllabus file (PDF), extracts its text, analyzes it with an AI
    to find a summary and key dates, and returns the structured data.
    """
    # 1. Extract text from the uploaded PDF file
    print(f"Processing file: {file.filename}")
    syllabus_text = await extract_text_from_file(file)

    # 2. Send the text to the AI for analysis
    print("Sending extracted text to AI for analysis...")
    
    # --- THIS IS THE CHANGE ---
    # Get the current date and pass it as context
    today = date.today()
    analysis_result = await extract_analysis_from_text(syllabus_text, today)
    # --- END OF CHANGE ---

    if not analysis_result:
        raise HTTPException(
            status_code=500,
            detail="Failed to get a valid analysis from the AI model."
        )

    # 3. Return the structured result
    print("Analysis complete. Returning structured data.")
    return analysis_result

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)