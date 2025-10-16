# app/main.py
from dotenv import load_dotenv
load_dotenv() # reads env file

import os
import shutil
from canvasapi import Canvas
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from typing import List

# --- Import custom modules and models ---
from .models import AiAnalysisResult, Course, FinalApiResponse, ScheduledEvent
from .ai_processor import extract_analysis_from_text
from .file_reader import extract_text_from_file
from .canvas_scheduler import schedule_event_in_canvas
from .calendar_sync import get_canvas_ical_feed, add_calendar_subscription

# --- Initialize FastAPI App ---
app = FastAPI(title="AI Scheduling Assistant API")

# Starlett Middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY"),
    https_only=False,
)

# OAuth 2.0
oauth = OAuth()

# Google OAuth
oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile https://www.googleapis.com/auth/calendar'},
    access_type='offline',
    prompt='consent'
)

# --- API Routes ---
"""Google"""
# Test homepage
@app.get('/')
async def homepage(request: Request):
    user = request.session.get('user')
    if user:
        return HTMLResponse(f'''
            <h1>Hello, {user["name"]}!</h1>
            <a href="/logout">Logout</a><br>
            <a href="/sync-calendar" style="font-weight: bold; color: blue;">Sync Canvas Calendar to Google</a>
        ''')
    return HTMLResponse('<h1>Welcome!</h1><a href="/login">Login with Google</a>')

@app.get('/login')
async def login(request: Request):
    redirect_uri = request.url_for('auth')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get('/auth')
async def auth(request: Request):
    """
    This is the callback route.
    It fetches the access token and stores both user info and the token in the session.
    """
    try:
        token = await oauth.google.authorize_access_token(request)

        request.session['user'] = dict(token.get('userinfo'))
        request.session['google_auth_token'] = dict(token)

    except Exception as e:
        return HTMLResponse(f"<h1>Login Failed: {e}</h1>")
    
    return RedirectResponse(url='/')

@app.get('/profile')
async def profile(request: Request):
    """A protected route that requires a valid session."""
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url='/')

    return HTMLResponse(f"""
        <h1>Welcome, {user.get('name')}!</h1>
        <p>Email: {user.get('email')}</p>
        <p>Profile Picture: <img src="{user.get('picture')}" alt="Profile Picture"></p>
        <a href="/">Home</a> | <a href="/logout">Logout</a>
    """)

@app.get('/logout')
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url='/')
"""-------"""

"""Upload File"""
@app.post("/api/documents/schedule-from-file/", response_model=FinalApiResponse)
async def upload_and_schedule(
    course_id: int = Form(...),
    file: UploadFile = File(...)
):

    temp_file_path = f"temp_{file.filename}"
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        print(f"Extracting text from {file.filename}...")
        document_text = extract_text_from_file(temp_file_path)
        if not document_text:
            raise HTTPException(status_code=400, detail="Could not extract text from file.")

        print("Sending text to AI for analysis...")
        ai_result: AiAnalysisResult = extract_analysis_from_text(document_text)
        if not ai_result or not ai_result.events:
            raise HTTPException(status_code=400, detail="AI could not identify any events in the document.")

        print(f"Scheduling {len(ai_result.events)} events in Canvas for course {course_id}...")
        scheduled_events_list: List[ScheduledEvent] = []
        for event in ai_result.events:
            canvas_event = schedule_event_in_canvas(
                api_url=canvas_api_url,
                api_key=canvas_api_key,
                course_id=course_id,
                event_data=event
            )
            if canvas_event:
                scheduled_events_list.append(canvas_event)

        if not scheduled_events_list:
            raise HTTPException(status_code=500, detail="Failed to schedule any events in Canvas.")

        return FinalApiResponse(
            source_file_name=file.filename,
            summary=ai_result.summary,
            scheduled_events=scheduled_events_list
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.get('/sync-calendar')
async def sync_calendar(request: Request):
    google_token = request.session.get('google_auth_token')

    if not google_token:
        return RedirectResponse(url='/login')

    try:
        ical_url = get_canvas_ical_feed()

        result = add_calendar_subscription(google_token, ical_url)

        return HTMLResponse(
            f"<h1>Success!</h1>"
            f"<p>Your Google Calendar is now subscribed to your Canvas Calendar: '{result.get('summary')}'.</p>"
            f"<p>It may take a few moments for events to appear.</p>"
            f"<a href='/'>Go Home</a>"
        )

    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url='/login')
        return HTMLResponse(f"<h1>Error</h1><p>{e.detail}</p>", status_code=e.status_code)
    except Exception as e:
        return HTMLResponse(f"<h1>Error</h1><p>{str(e)}</p>", status_code=500)
"""------"""

"""Get Courses"""

@app.get("/api/canvas/courses", response_model=List[Course])
def get_user_courses(request: Request):
    """
    Fetches a list of the current user's courses from Canvas
    using the personal API key from the .env file.
    """
    canvas_api_url = os.getenv("CANVAS_API_URL")
    canvas_api_key = os.getenv("CANVAS_API_KEY")

    if not canvas_api_url or not canvas_api_key:
        raise HTTPException(status_code=500, detail="Canvas credentials not configured.")

    try:
        canvas = Canvas(canvas_api_url, canvas_api_key)

        courses_list = canvas.get_courses(enrollment_state='active')

        courses = [{"id": c.id, "name": c.name} for c in courses_list]
        return courses

    except Exception as e:
        print(f"Error fetching Canvas courses: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch courses from Canvas.")
    """-------"""