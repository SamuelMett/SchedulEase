# app/main.py
from dotenv import load_dotenv
load_dotenv() # reads env file

import os
import shutil
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from typing import List

# --- Import custom modules and models ---
from .models import AiAnalysisResult, FinalApiResponse, ScheduledEvent
from .ai_processor import extract_analysis_from_text
from .file_reader import extract_text_from_file
from .canvas_scheduler import schedule_event_in_canvas

# --- Load Environment Variables ---
CANVAS_API_URL = os.getenv("CANVAS_API_URL")
CANVAS_API_KEY = os.getenv("CANVAS_API_KEY")

if not all([CANVAS_API_URL, CANVAS_API_KEY, os.getenv("OPENAI_API_KEY")]):
    raise ValueError("Missing required environment variables.")

# --- Initialize FastAPI App ---
app = FastAPI(title="AI Scheduling Assistant API")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5001", "https://localhost:7082"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Starlett Middleware
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY"))

# OAuth 2.0
oauth = OAuth()

# Google OAuth
oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Canvas OAuth
oauth.register(
    name='canvas',
    client_id=os.getenv("CANVAS_CLIENT_ID"),
    client_secret=os.getenv("CANVAS_CLIENT_SECRET"),
    access_token_url=f'{os.getenv("CANVAS_API_URL")}/login/oauth2/token',
    authorize_url=f'{os.getenv("CANVAS_API_URL")}/login/oauth2/auth',
    api_base_url=f'{os.getenv("CANVAS_API_URL")}/api/v1/',
    client_kwargs={'scope': 'url:GET|/api/v1/users/:user_id/profile url:POST|/api/v1/calendar_events'} # Example scopes
)


# --- API Routes ---
"""Google"""
@app.get('/')
async def homepage(request: Request):
    user = request.session.get('user')
    if user:
        return HTMLResponse(f'<h1>Hello, {user["name"]}!</h1><a href="/logout">Logout</a><br><a href="/connect/canvas">Connect to Canvas</a>')
    return HTMLResponse('<h1>Welcome!</h1><a href="/login">Login with Google</a>')

@app.get('/login')
async def login(request: Request):
    redirect_uri = request.url_for('auth')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get('/auth')
async def auth(request: Request):
    token = await oauth.google.authorize_access_token(request)
    request.session['user'] = token.get('userinfo')
    return RedirectResponse(url='/')

@app.get('/logout')
async def logout(request: Request):
    request.session.pop('user', None)
    return RedirectResponse(url='/')
"""-------"""

""" Canvas """
@app.get('/connect/canvas')
async def connect_canvas(request: Request):
    # Ensure user is logged in first
    if not request.session.get('user'):
        return RedirectResponse(url='/')
    
    redirect_uri = request.url_for('canvas_auth')
    return await oauth.canvas.authorize_redirect(request, redirect_uri)

@app.get('/canvas/auth')
async def canvas_auth(request: Request):
    token = await oauth.canvas.authorize_access_token(request)
    
    # Securely store the token (e.g., in a database) associated with the logged-in user.
    # For this example, we'll just put it in the session.
    request.session['canvas_token'] = token
    print("Canvas Token Acquired:", token)
    
    # You can now use this token to make API calls
    # Example: Fetching user profile from Canvas
    resp = await oauth.canvas.get('users/self/profile', token=token)
    profile = resp.json()
    
    return HTMLResponse(f"<h1>Canvas Connected!</h1><p>Canvas Name: {profile.get('name')}</p><a href='/'>Go Home</a>")
"""-----"""

"""Upload File"""
@app.post("/api/documents/schedule-from-file/", response_model=FinalApiResponse)
async def upload_and_schedule(
    course_id: int = Form(...),
    file: UploadFile = File(...)
):

    # 1. Save the uploaded file temporarily
    temp_file_path = f"temp_{file.filename}"
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # 2. Extract text from the saved file
        print(f"Extracting text from {file.filename}...")
        document_text = extract_text_from_file(temp_file_path)
        if not document_text:
            raise HTTPException(status_code=400, detail="Could not extract text from file.")

        # 3. Get structured data from OpenAI
        print("Sending text to AI for analysis...")
        ai_result: AiAnalysisResult = extract_analysis_from_text(document_text)
        if not ai_result or not ai_result.events:
            raise HTTPException(status_code=400, detail="AI could not identify any events in the document.")

        # 4. Schedule events in Canvas
        print(f"Scheduling {len(ai_result.events)} events in Canvas for course {course_id}...")
        scheduled_events_list: List[ScheduledEvent] = []
        for event in ai_result.events:
            canvas_event = schedule_event_in_canvas(
                api_url=CANVAS_API_URL,
                api_key=CANVAS_API_KEY,
                course_id=course_id,
                event_data=event
            )
            if canvas_event:
                scheduled_events_list.append(canvas_event)

        if not scheduled_events_list:
            raise HTTPException(status_code=500, detail="Failed to schedule any events in Canvas.")

        # 5. Build and return the final response
        return FinalApiResponse(
            source_file_name=file.filename,
            summary=ai_result.summary,
            scheduled_events=scheduled_events_list
        )

    except Exception as e:
        # Catch any other errors and report them
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # 6. Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
"""------"""