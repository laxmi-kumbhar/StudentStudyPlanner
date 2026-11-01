from datetime import datetime, date
from database.db import query_db, execute_db

def log_study_session(user_id: int, subject_id: int, duration_minutes: int, session_type: str = 'pomodoro', notes: str = '', task_id: int = None):
    """Log a completed focus session into SQLite."""
    res = execute_db("""
        INSERT INTO study_sessions (user_id, subject_id, task_id, duration_minutes, session_type, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, subject_id, task_id, duration_minutes, session_type, notes))
    return res['lastrowid']

def get_today_focus_summary(user_id: int):
    """Get total focus minutes, session count, and goal progress for today."""
    today_str = date.today().strftime("%Y-%m-%d")
    
    # User's daily goal
    user = query_db("SELECT daily_goal_minutes FROM users WHERE id = ?", (user_id,), one=True)
    daily_goal = user['daily_goal_minutes'] if user and user['daily_goal_minutes'] else 120
    
    # Sessions completed today
    stats = query_db("""
        SELECT 
            COALESCE(SUM(duration_minutes), 0) as total_minutes,
            COUNT(id) as total_sessions
        FROM study_sessions
        WHERE user_id = ? AND DATE(created_at) = DATE(?)
    """, (user_id, today_str), one=True)
    
    total_mins = stats['total_minutes'] or 0
    sessions_count = stats['total_sessions'] or 0
    goal_pct = min(round((total_mins / daily_goal) * 100), 100) if daily_goal > 0 else 0
    
    # Subject breakdown for today
    today_by_subject = query_db("""
        SELECT s.name, s.color, SUM(ss.duration_minutes) as minutes
        FROM study_sessions ss
        JOIN subjects s ON ss.subject_id = s.id
        WHERE ss.user_id = ? AND DATE(ss.created_at) = DATE(?)
        GROUP BY s.id
        ORDER BY minutes DESC
    """, (user_id, today_str))
    
    return {
        "today_minutes": total_mins,
        "today_hours": round(total_mins / 60.0, 1),
        "today_sessions": sessions_count,
        "daily_goal_minutes": daily_goal,
        "goal_percentage": goal_pct,
        "by_subject": today_by_subject
    }

def get_recent_sessions(user_id: int, limit: int = 10):
    """Retrieve recent study session logs."""
    return query_db("""
        SELECT ss.*, s.name as subject_name, s.color as subject_color, t.title as task_title
        FROM study_sessions ss
        LEFT JOIN subjects s ON ss.subject_id = s.id
        LEFT JOIN tasks t ON ss.task_id = t.id
        WHERE ss.user_id = ?
        ORDER BY ss.created_at DESC
        LIMIT ?
    """, (user_id, limit))
