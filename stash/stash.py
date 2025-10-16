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