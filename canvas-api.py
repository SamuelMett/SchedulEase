# Import the Canvas class
from canvasapi import Canvas
from datetime import datetime, timezone
# Create your own config.py file and add your API_URL and API_KEY
import config

print("Please log in using your google account")

# Initialize a new Canvas object
canvas = Canvas(config.API_URL, config.API_KEY)

# instantiate user
user = canvas.get_user(1111)

print("Is this your account?: yes or no")

print("ID", user.id)
print("Name: ", user.name)

# example OAuth2.0 to get into the Google SSO
confirm = input()
if confirm == "yes":
    print("Great! You have been authenticated")
else:
    print("Please get out of here/change account")

# loop program until quit
while quit != True:

    # Fall semester start and end (example: Fall 2026)
    fall_start = datetime(2025, 8, 15, 0, 0, 0, tzinfo=timezone.utc)
    fall_end   = datetime(2025, 12, 15, 23, 59, 59, tzinfo=timezone.utc)
    # Spring semester start and end (example: Spring 2026)
    spring_start = datetime(2026, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
    spring_end   = datetime(2026, 5, 15, 23, 59, 59, tzinfo=timezone.utc)

    # get all courses that are currently enrolled
    courses = canvas.get_courses(enrollment_state="active")

    # options for current functions
    print("Please choose an option")
    print("1. show current enrolled courses")
    print("2. show current logged-in user")
    print("3. show current assignments scheduled")
    print("4. show all events scheduled for the current semester")
    print("0. quit the program")
    option = input()

    if option == "1":
        print("Your courses are: ")
        for course in courses:
            print(course)

    if option == "2":
        print(user.name, user.id)

    if option == "3":
        for course in courses:
            assignments = course.get_assignments()
            for a in assignments:
                if a.due_at and fall_start.isoformat() <= a.due_at[:10] <= fall_end.isoformat():
                    print(f"[ASSIGNMENT] {a.name} | {a.due_at} | {course.name}")

    if option == "4":
        # get all assignments. can also be test/quiz/event
        for course in courses:
            assignments = course.get_assignments()
            for a in assignments:
                if a.due_at and fall_start.isoformat() <= a.due_at[:10] <= fall_end.isoformat():
                    print(f"[ASSIGNMENT] {a.name} | {a.due_at} | {course.name}")
        # get all quizzes
        for course in courses:
            try:
                quizzes = course.get_quizzes()
                for q in quizzes:
                    if q.due_at and fall_start.isoformat() <= q.due_at[:10] <= fall_end.isoformat():
                        print(f"[QUIZ] {q.title} | {q.due_at} | {course.name}")
            except Exception:
                pass  # not all courses have quizzes
        # get all discussion posts
        for course in courses:
            discussions = course.get_discussion_topics()
            for d in discussions:
                if d.due_at and fall_start.isoformat() <= d.due_at[:10] <= fall_end.isoformat():
                    print(f"[DISCUSSION] {d.title} | {d.due_at} | {course.name}")

    # quit command
    if option == "0":
        quit = True
