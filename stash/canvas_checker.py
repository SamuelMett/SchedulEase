# app/canvas_checker.py

from fastapi import HTTPException
from canvasapi import Canvas
from canvasapi.exceptions import Unauthorized, ResourceNotFound

def check_canvas_permissions(api_url: str, api_key: str, course_id: int):
    """
    Checks if the API key is valid and if the user has access to the course.
    Raises HTTPException on failure. Returns a valid Canvas object on success.
    """
    try:
        canvas = Canvas(api_url, api_key)
        # This call will fail if the API key is invalid.
        user = canvas.get_current_user()
        # This call will fail if the course doesn't exist or the user can't see it.
        course = canvas.get_course(course_id)
        print(f"Permission check passed for user '{user.name}' in course '{course.name}'.")
        return canvas, user

    except Unauthorized:
        print("Canvas permission check failed: Unauthorized.")
        raise HTTPException(
            status_code=401,
            detail="Unauthorized. Your Canvas API key is invalid or has expired."
        )
    except ResourceNotFound:
        print("Canvas permission check failed: Course not found.")
        raise HTTPException(
            status_code=404,
            detail=f"Course with ID {course_id} was not found or you do not have permission to access it."
        )
    except Exception as e:
        print(f"An unexpected error occurred during Canvas permission check: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while communicating with Canvas."
        )