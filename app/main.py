# app/main.py
from dotenv import load_dotenv

load_dotenv()

import os
import uvicorn

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware

from fastapi import UploadFile, File, HTTPException
from .models import AiAnalysisResult
from .ai_processor import extract_analysis_from_text
from .file_reader import extract_text_from_file
from pathlib import Path

# Load environment variables from .env file

# --- ADD THIS DEBUG LINE ---
print(f"--- .env check --- OpenAI Key Found: {'OPENAI_API_KEY' in os.environ}")

print(f"SECRET_KEY loaded: {os.getenv('SECRET_KEY') is not None}")

# --- Initialize FastAPI App ---
app = FastAPI(title="Google OAuth 2.0 Example")

# --- Middleware ---
# SessionMiddleware is required for Authlib's OAuth client to store temporary state
# and the final user session.
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY"),
    session_cookie="session",  # Name of the cookie
    same_site="lax",           # CSRF protection
    https_only=False           # Set to True in production
)

# --- OAuth 2.0 Setup with Authlib ---
oauth = OAuth()

# Register the Google OAuth client
oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
client_kwargs={
        'scope': 'openid email profile https://www.googleapis.com/auth/calendar.readonly'
    },
    access_type='offline',
    prompt='consent' 
)

# --- API Routes ---

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
            <a href="/calendar">View Your Google Calendar Events</a><br>
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
        
        # --- Start Debugging ---
        print("----------- Google Token Received -----------")
        print(token)
        print("---------------------------------------------")
        
    except Exception as e:
        # If there's an error, this will print it to your console
        print(f"Error during authorize_access_token: {e}")
        return HTMLResponse(f"<h1>Error logging in: {e}</h1>")
    
    user_info = token.get('userinfo')
    
    # --- More Debugging ---
    print("----------- User Info Extracted -----------")
    print(user_info)
    print("-------------------------------------------")

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

@app.get('/calendar', response_class=HTMLResponse)
async def calendar(request: Request):
    token = request.session.get('token')
    if not token:
        return RedirectResponse(url='/login')

    # --- START DEBUGGING ---
    # This will print the raw token to your uvicorn terminal
    access_token = token.get('access_token')
    print("\n--- GOOGLE ACCESS TOKEN ---")
    print(access_token)
    print("---------------------------\n")
    # --- END DEBUGGING ---

    try:
        resp = await oauth.google.get(
            'https://www.googleapis.com/calendar/v3/calendars/primary/events',
            token=token
        )
        resp.raise_for_status()
        events = resp.json()
        
        event_list = "<ul>"
        for event in events.get('items', []):
            event_list += f"<li>{event.get('summary')} ({event.get('start', {}).get('dateTime', 'All day')})</li>"
        event_list += "</ul>"

        return f"""
            <h1>Your Upcoming Google Calendar Events</h1>
            {event_list}
            <a href="/">Home</a>
        """

    except Exception as e:
        return HTMLResponse(f"<h1>Could not fetch calendar events: {e}</h1>")
    
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
    analysis_result = extract_analysis_from_text(syllabus_text)

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