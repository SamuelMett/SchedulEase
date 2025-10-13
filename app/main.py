# app/main.py
from dotenv import load_dotenv
load_dotenv() # reads env file

import os
import shutil
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
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

# Add CORS middleware for Blazor frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5001", "https://localhost:7082"], # Add your Blazor URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- API Endpoint ---
@app.post("/api/documents/schedule-from-file/", response_model=FinalApiResponse)
async def upload_and_schedule(
    course_id: int = Form(...),
    file: UploadFile = File(...)
):
    """
    This endpoint processes a file, extracts events with AI, and schedules them in Canvas.
    """
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