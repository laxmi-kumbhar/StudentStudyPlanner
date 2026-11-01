import functools
import re
from flask import session, redirect, url_for, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import query_db, execute_db

def hash_password(password: str) -> str:
    """Hash plain text password with Werkzeug security."""
    return generate_password_hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed string."""
    if not hashed_password:
        return False
    return check_password_hash(hashed_password, plain_password)

def is_valid_email(email: str) -> bool:
    """Validate email address format."""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email.strip()))

def get_current_user_id():
    """Retrieve logged in user ID from session. Returns None if not authenticated."""
    return session.get('user_id')

def get_current_user():
    """Fetch complete current user record."""
    user_id = get_current_user_id()
    if not user_id:
        return None
    return query_db("""
        SELECT id, username, email, avatar_color, daily_goal_minutes, auth_provider, google_id, avatar_url, created_at
        FROM users WHERE id = ?
    """, (user_id,), one=True)

def login_required(view):
    """Decorator to require login for specific API endpoints or views."""
    @functools.wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get('user_id'):
            if request.path.startswith('/api/'):
                return jsonify({"success": False, "error": "Unauthorized. Please log in."}), 401
            return redirect(url_for('views.login'))
        return view(*args, **kwargs)
    return wrapped_view

def seed_starter_data_for_user(user_id: int):
    """Populate initial starter subjects, timetable slots, exams, and a welcome task for a brand new user."""
    existing_subjects = query_db("SELECT id FROM subjects WHERE user_id = ? LIMIT 1", (user_id,), one=True)
    if existing_subjects:
        return

    starter_subjects = [
        ("Mathematics & Statistics", "MATH-101", "#6366f1", "book", 5.0),
        ("Computer Science & Programming", "CS-101", "#06b6d4", "code-2", 6.0),
        ("Physics & Science", "SCI-101", "#ec4899", "cpu", 4.0),
    ]
    created_subjects = {}
    for name, code, color, icon, hours in starter_subjects:
        res = execute_db("""
            INSERT INTO subjects (user_id, name, code, color, icon, target_hours_per_week)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, name, code, color, icon, hours))
        subject_id = res['lastrowid']
        created_subjects[code] = subject_id
        execute_db("""
            INSERT INTO topics (subject_id, user_id, title, is_completed)
            VALUES (?, ?, ?, 0)
        """, (subject_id, user_id, "Module 1: Introduction & Fundamentals"))

    # Starter Timetable Slots (0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri)
    math_id = created_subjects.get("MATH-101")
    cs_id = created_subjects.get("CS-101")
    sci_id = created_subjects.get("SCI-101")

    timetable_slots = [
        (math_id, 0, "09:00", "10:30", "Room 101 - Math Wing"),
        (cs_id,   0, "11:00", "12:30", "CS Computer Lab 2"),
        (sci_id,  1, "10:00", "11:30", "Physics Lecture Hall B"),
        (math_id, 2, "09:00", "10:30", "Room 101 - Math Wing"),
        (cs_id,   2, "13:00", "14:30", "CS Computer Lab 2"),
        (sci_id,  3, "10:00", "11:30", "Physics Lecture Hall B"),
        (cs_id,   4, "10:00", "11:30", "CS Computer Lab 2"),
    ]
    for sid, day, st, et, loc in timetable_slots:
        if sid:
            execute_db("""
                INSERT INTO timetable_slots (user_id, subject_id, day_of_week, start_time, end_time, location)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, sid, day, st, et, loc))

    # Starter Exam
    if math_id:
        execute_db("""
            INSERT INTO exams (user_id, subject_id, title, exam_date, room_or_link, notes, weight_percentage)
            VALUES (?, ?, 'Midterm Exam: Mathematics & Calculus', date('now', '+12 days'), 'Exam Hall 2', 'Chapters 1 to 4', 30.0)
        """, (user_id, math_id))

    execute_db("""
        INSERT INTO tasks (user_id, subject_id, title, description, priority, status, due_date, estimated_minutes)
        VALUES (?, NULL, 'Welcome to StudyFlow! 🚀 Plan your first study session', 'Explore courses, track tasks on the Kanban board, and start a Pomodoro timer in the Focus Room.', 'high', 'todo', date('now', '+2 days'), 25)
    """, (user_id,))
