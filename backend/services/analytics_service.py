from datetime import datetime, date, timedelta
from database.db import query_db

def calculate_study_streak(user_id: int) -> int:
    """Calculate the consecutive days study streak for a user."""
    # Get all distinct active study dates ordered descending
    rows = query_db("""
        SELECT DISTINCT DATE(created_at) as study_date
        FROM study_sessions
        WHERE user_id = ?
        ORDER BY study_date DESC
    """, (user_id,))
    
    if not rows:
        return 0
    
    study_dates = {datetime.strptime(r['study_date'], "%Y-%m-%d").date() for r in rows}
    
    today = date.today()
    streak = 0
    current_check = today
    
    # If not studied today yet, check if studied yesterday to keep the streak alive
    if today not in study_dates:
        current_check = today - timedelta(days=1)
        if current_check not in study_dates:
            return 0
    
    while current_check in study_dates:
        streak += 1
        current_check -= timedelta(days=1)
        
    return streak

def get_weekly_study_trend(user_id: int):
    """Retrieve study minutes for each of the last 7 days for Chart.js rendering."""
    today = date.today()
    days = []
    labels = []
    minutes_data = []
    
    for i in range(6, -1, -1):
        day_date = today - timedelta(days=i)
        days.append(day_date.strftime("%Y-%m-%d"))
        labels.append(day_date.strftime("%a (%b %d)"))
    
    # Query aggregated minutes per day
    rows = query_db("""
        SELECT DATE(created_at) as study_date, SUM(duration_minutes) as total_mins
        FROM study_sessions
        WHERE user_id = ? AND DATE(created_at) >= DATE(?)
        GROUP BY DATE(created_at)
    """, (user_id, days[0]))
    
    day_map = {r['study_date']: r['total_mins'] for r in rows}
    
    for d in days:
        minutes_data.append(day_map.get(d, 0))
        
    return {
        "labels": labels,
        "minutes": minutes_data,
        "hours": [round(m / 60.0, 1) for m in minutes_data]
    }

def get_subject_time_distribution(user_id: int):
    """Retrieve total study time per subject for Doughnut chart."""
    rows = query_db("""
        SELECT s.name, s.color, COALESCE(SUM(ss.duration_minutes), 0) as total_minutes
        FROM subjects s
        LEFT JOIN study_sessions ss ON s.id = ss.subject_id
        WHERE s.user_id = ?
        GROUP BY s.id
        HAVING total_minutes > 0
        ORDER BY total_minutes DESC
    """, (user_id,))
    
    labels = [r['name'] for r in rows]
    colors = [r['color'] for r in rows]
    minutes = [r['total_minutes'] for r in rows]
    hours = [round(r['total_minutes'] / 60.0, 1) for r in rows]
    
    return {
        "labels": labels,
        "colors": colors,
        "minutes": minutes,
        "hours": hours
    }

def get_overall_dashboard_stats(user_id: int):
    """Get all high-level stats for the main dashboard."""
    # 1. Total study minutes
    all_time = query_db("""
        SELECT COALESCE(SUM(duration_minutes), 0) as total_mins, COUNT(id) as total_sessions
        FROM study_sessions WHERE user_id = ?
    """, (user_id,), one=True)
    
    total_minutes = all_time['total_mins'] if all_time else 0
    total_hours = round(total_minutes / 60.0, 1)
    
    # 2. This week's study minutes
    monday = date.today() - timedelta(days=date.today().weekday())
    this_week = query_db("""
        SELECT COALESCE(SUM(duration_minutes), 0) as week_mins
        FROM study_sessions WHERE user_id = ? AND DATE(created_at) >= DATE(?)
    """, (user_id, monday.strftime("%Y-%m-%d")), one=True)
    week_hours = round((this_week['week_mins'] if this_week else 0) / 60.0, 1)
    
    # 3. Tasks stats
    task_stats = query_db("""
        SELECT 
            COUNT(id) as total_tasks,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
            SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress_tasks,
            SUM(CASE WHEN status = 'todo' THEN 1 ELSE 0 END) as todo_tasks
        FROM tasks WHERE user_id = ?
    """, (user_id,), one=True)
    
    total_tasks = task_stats['total_tasks'] or 0
    completed_tasks = task_stats['completed_tasks'] or 0
    task_completion_rate = round((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0
    
    # 4. Subjects count
    subjects_count = query_db("SELECT COUNT(id) as count FROM subjects WHERE user_id = ?", (user_id,), one=True)
    
    # 5. Streak
    streak = calculate_study_streak(user_id)
    
    # 6. Upcoming exams (next 30 days)
    upcoming_exams = query_db("""
        SELECT e.*, s.name as subject_name, s.color as subject_color
        FROM exams e
        JOIN subjects s ON e.subject_id = s.id
        WHERE e.user_id = ? AND e.exam_date >= datetime('now')
        ORDER BY e.exam_date ASC
        LIMIT 4
    """, (user_id,))
    
    return {
        "total_hours": total_hours,
        "week_hours": week_hours,
        "total_sessions": all_time['total_sessions'] if all_time else 0,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "in_progress_tasks": task_stats['in_progress_tasks'] or 0,
        "todo_tasks": task_stats['todo_tasks'] or 0,
        "task_completion_rate": task_completion_rate,
        "total_subjects": subjects_count['count'] if subjects_count else 0,
        "study_streak": streak,
        "upcoming_exams": upcoming_exams
    }

def get_user_badges(user_id: int):
    """Compute unlockable milestone and gamification badges for the student."""
    stats = get_overall_dashboard_stats(user_id)
    total_hours = stats.get('total_hours', 0)
    completed_tasks = stats.get('completed_tasks', 0)
    streak = stats.get('study_streak', 0)
    subjects_count = stats.get('total_subjects', 0)
    total_sessions = stats.get('total_sessions', 0)

    badges = [
        {
            "id": "streak",
            "title": "Streak Pioneer",
            "icon": "🔥",
            "desc": "Maintain 3+ consecutive days of study",
            "unlocked": streak >= 3,
            "progress": min(streak, 3),
            "max": 3,
            "tier": "Gold" if streak >= 7 else ("Silver" if streak >= 3 else "Bronze")
        },
        {
            "id": "deep_work",
            "title": "Deep Work Master",
            "icon": "⏱️",
            "desc": "Log 10+ hours of focused study time",
            "unlocked": total_hours >= 10.0,
            "progress": min(total_hours, 10.0),
            "max": 10.0,
            "tier": "Master" if total_hours >= 25 else ("Gold" if total_hours >= 10 else "Bronze")
        },
        {
            "id": "task_crusher",
            "title": "Task Conqueror",
            "icon": "🎯",
            "desc": "Complete 5+ academic assignments & tasks",
            "unlocked": completed_tasks >= 5,
            "progress": min(completed_tasks, 5),
            "max": 5,
            "tier": "Gold" if completed_tasks >= 10 else ("Silver" if completed_tasks >= 5 else "Bronze")
        },
        {
            "id": "curriculum",
            "title": "Academic Polymath",
            "icon": "📚",
            "desc": "Actively enrolled in 3+ courses & subjects",
            "unlocked": subjects_count >= 3,
            "progress": min(subjects_count, 3),
            "max": 3,
            "tier": "Silver" if subjects_count >= 3 else "Bronze"
        },
        {
            "id": "focus_sessions",
            "title": "Flow State Scholar",
            "icon": "🧘",
            "desc": "Complete 5+ Pomodoro & focus sessions",
            "unlocked": total_sessions >= 5,
            "progress": min(total_sessions, 5),
            "max": 5,
            "tier": "Gold" if total_sessions >= 10 else ("Silver" if total_sessions >= 5 else "Bronze")
        }
    ]
    return badges

