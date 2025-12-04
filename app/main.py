# app/main.py

from app import calendar_api
from dotenv import load_dotenv
load_dotenv()

from fastapi.middleware.cors import CORSMiddleware
import os
import uuid  # ADD THIS
import uvicorn
from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from typing import List, Literal
from datetime import datetime, timezone, date
from pydantic import BaseModel
from openai import OpenAI

from .models import AiAnalysisResult, ScheduledEvent, EventFromSelector
from .ai_processor import extract_analysis_from_text
from .file_reader import extract_text_from_file
from .google_scheduler import schedule_event_on_google_calendar, schedule_multiple_events
from app.routers import chat as chat_router

app = FastAPI(title="SchedulEase API")

# Initialize OpenAI client (MOVE THIS UP)
client = OpenAI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:7070"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY"),
    session_cookie="session",
    same_site="lax",
    https_only=False
)

# OAuth setup
oauth = OAuth()
app.state.oauth = oauth

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

# Routers
app.include_router(calendar_api.router)
app.include_router(chat_router.router, prefix="/api/chat", tags=["Chat API"])



@app.get('/', response_class=HTMLResponse)
async def homepage(request: Request):
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
    redirect_uri = "http://127.0.0.1:8000/auth"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get('/auth')
async def auth(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        print(f"Error during authorize_access_token: {e}")
        return HTMLResponse(f"<h1>Error logging in: {e}</h1>")

    user_info = token.get('userinfo')
    if user_info:
        request.session['user'] = dict(user_info)
        request.session['token'] = token

        return RedirectResponse(url='/')


@app.get('/logout')
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url='/')


@app.get('/profile', response_class=HTMLResponse)
async def profile(request: Request):
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


# ----------------------------
#     SYLLABUS UPLOAD
# ----------------------------

@app.post("/upload-syllabus", response_model=AiAnalysisResult)
async def upload_and_analyze_syllabus(file: UploadFile = File(...)):
    print(f"Processing file: {file.filename}")

    syllabus_text = await extract_text_from_file(file)
    today = date.today()
    analysis_result = await extract_analysis_from_text(syllabus_text, today)

    if not analysis_result:
        raise HTTPException(
            status_code=500,
            detail="Failed to get a valid analysis from the AI model."
        )

    return analysis_result


# ----------------------------
#   STUDY MATERIAL GENERATION
# ----------------------------

# ADD THESE MODELS
class GenerateStudyMaterialRequest(BaseModel):
    eventTitle: str
    eventStart: datetime
    eventEnd: datetime


class StudyMaterialResponse(BaseModel):
    id: str
    eventTitle: str
    eventDate: datetime
    content: str
    createdAt: datetime


@app.post("/api/study-material/generate", response_model=StudyMaterialResponse)
async def generate_study_material(request: GenerateStudyMaterialRequest):
    """
    Generate study material for a calendar event using OpenAI
    """
    try:
        # Calculate event duration
        duration = request.eventEnd - request.eventStart
        duration_hours = duration.total_seconds() / 3600
        
        # Create a prompt for the AI model
        prompt = f"""You are an intelligent study assistant. A student has a calendar event titled "{request.eventTitle}" scheduled on {request.eventStart.strftime("%B %d, %Y at %I:%M %p")} for {duration_hours:.1f} hours.

Generate comprehensive study material for this event. Include:
1. **Overview**: Brief description of what this event is about
2. **Key Topics**: Main subjects or areas to focus on
3. **Study Tips**: Specific strategies for preparing for this event
4. **Time Management**: Recommended study schedule leading up to the event
5. **Important Notes**: Any critical information or reminders

Make the study material detailed, actionable, and tailored to the event title. If it appears to be an exam or test, focus on exam preparation strategies. If it's a presentation, focus on presentation skills. If it's homework, focus on completing the assignment effectively.

Keep the content well-structured, clear, and student-friendly."""

        # Call OpenAI API
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert academic study assistant helping students prepare for their academic events."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
        )
        
        # Extract the generated content
        study_content = completion.choices[0].message.content or "Failed to generate content"
        
        # Create response
        study_material = StudyMaterialResponse(
            id=str(uuid.uuid4()),
            eventTitle=request.eventTitle,
            eventDate=request.eventStart,
            content=study_content,
            createdAt=datetime.now()
        )
        
        return study_material
        
    except Exception as e:
        print(f"Error generating study material: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate study material: {str(e)}"
        )


# ----------------------------
#        CHAT ENDPOINT
# ----------------------------

class ChatTurn(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatTurn]


class ScheduleQuestion(BaseModel):
    question: str


class ChatReply(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatReply)
async def chat(req: ChatRequest):
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages required")

    msgs = [{
        "role": "system",
        "content": (
            "You are SchedulEase, an academic assistant. "
            "Be concise and helpful. If asked about due dates, "
            "explain what you can do with ICS/Google Calendar in this app."
        )
    }]

    msgs += [{"role": m.role, "content": m.content} for m in req.messages]

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=msgs,
        temperature=0.2,
    )

    text = completion.choices[0].message.content or "..."
    return ChatReply(reply=text)


# ----------------------------
#        MAIN
# ----------------------------

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)