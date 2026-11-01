from flask import Blueprint, render_template, session, redirect, url_for, current_app
from datetime import date
from backend.utils.auth_helpers import get_current_user_id, get_current_user, login_required
from backend.services.analytics_service import get_overall_dashboard_stats, get_user_badges
from backend.services.subject_service import get_user_subjects
from backend.services.task_service import get_tasks, get_tasks_grouped, sync_completed_tasks_to_study_sessions
from backend.services.timer_service import get_today_focus_summary, get_recent_sessions
from database.db import query_db

views_bp = Blueprint('views', __name__)

@views_bp.route('/')
@login_required
def index_view():
    user_id = get_current_user_id()
    user = get_current_user()
    if not user:
        session.clear()
        return redirect(url_for('views.login'))
    sync_completed_tasks_to_study_sessions(user_id)
    stats = get_overall_dashboard_stats(user_id)
    badges = get_user_badges(user_id)
    subjects = get_user_subjects(user_id)
    focus_today = get_today_focus_summary(user_id)
    grouped_tasks = get_tasks_grouped(user_id)
    recent_sessions = get_recent_sessions(user_id, limit=20)
    
    # Get today's classes
    today_dow = date.today().weekday()
    today_classes = query_db("""
        SELECT ts.*, s.name as subject_name, s.color as subject_color, s.code as subject_code
        FROM timetable_slots ts
        JOIN subjects s ON ts.subject_id = s.id
        WHERE ts.user_id = ? AND ts.day_of_week = ?
        ORDER BY ts.start_time ASC
    """, (user_id, today_dow))
    
    # Timetable & Exams
    timetable = query_db("""
        SELECT ts.*, s.name as subject_name, s.color as subject_color, s.code as subject_code
        FROM timetable_slots ts
        JOIN subjects s ON ts.subject_id = s.id
        WHERE ts.user_id = ?
        ORDER BY ts.day_of_week, ts.start_time
    """, (user_id,))
    
    exams = query_db("""
        SELECT e.*, s.name as subject_name, s.color as subject_color
        FROM exams e
        JOIN subjects s ON e.subject_id = s.id
        WHERE e.user_id = ?
        ORDER BY e.exam_date ASC
    """, (user_id,))
    
    urgent_tasks = get_tasks(user_id, status='todo')[:4]
    
    return render_template('index.html',
                           user=user,
                           stats=stats,
                           badges=badges,
                           subjects=subjects,
                           tasks=grouped_tasks,
                           focus_today=focus_today,
                           today_classes=today_classes,
                           timetable=timetable,
                           exams=exams,
                           recent_sessions=recent_sessions,
                           urgent_tasks=urgent_tasks,
                           active_page='dashboard')

@views_bp.route('/dashboard')
@login_required
def dashboard():
    user_id = get_current_user_id()
    user = get_current_user()
    if not user:
        session.clear()
        return redirect(url_for('views.login'))
    sync_completed_tasks_to_study_sessions(user_id)
    stats = get_overall_dashboard_stats(user_id)
    subjects = get_user_subjects(user_id)
    focus_today = get_today_focus_summary(user_id)
    
    # Get today's classes (timetable)
    today_dow = date.today().weekday()
    today_classes = query_db("""
        SELECT ts.*, s.name as subject_name, s.color as subject_color, s.code as subject_code
        FROM timetable_slots ts
        JOIN subjects s ON ts.subject_id = s.id
        WHERE ts.user_id = ? AND ts.day_of_week = ?
        ORDER BY ts.start_time ASC
    """, (user_id, today_dow))
    
    # Priority tasks
    urgent_tasks = get_tasks(user_id, status='todo')[:4]
    badges = get_user_badges(user_id)
    
    return render_template('pages/dashboard.html',
                           user=user,
                           stats=stats,
                           badges=badges,
                           subjects=subjects,
                           focus_today=focus_today,
                           today_classes=today_classes,
                           urgent_tasks=urgent_tasks,
                           active_page='dashboard')

@views_bp.route('/subjects')
@login_required
def subjects():
    user_id = get_current_user_id()
    user = get_current_user()
    if not user:
        session.clear()
        return redirect(url_for('views.login'))
    user_subjects = get_user_subjects(user_id)
    return render_template('pages/subjects.html',
                           user=user,
                           subjects=user_subjects,
                           active_page='subjects')

@views_bp.route('/tasks')
@login_required
def tasks():
    user_id = get_current_user_id()
    user = get_current_user()
    if not user:
        session.clear()
        return redirect(url_for('views.login'))
    grouped_tasks = get_tasks_grouped(user_id)
    subjects = get_user_subjects(user_id)
    return render_template('pages/tasks.html',
                           user=user,
                           tasks=grouped_tasks,
                           subjects=subjects,
                           active_page='tasks')

@views_bp.route('/timer')
@login_required
def timer():
    user_id = get_current_user_id()
    user = get_current_user()
    if not user:
        session.clear()
        return redirect(url_for('views.login'))
    sync_completed_tasks_to_study_sessions(user_id)
    subjects = get_user_subjects(user_id)
    focus_today = get_today_focus_summary(user_id)
    recent_sessions = get_recent_sessions(user_id, limit=20)
    pending_tasks = get_tasks(user_id, status='todo')
    
    return render_template('pages/timer.html',
                           user=user,
                           subjects=subjects,
                           focus_today=focus_today,
                           recent_sessions=recent_sessions,
                           pending_tasks=pending_tasks,
                           active_page='timer')

@views_bp.route('/calendar')
@login_required
def calendar():
    user_id = get_current_user_id()
    user = get_current_user()
    if not user:
        session.clear()
        return redirect(url_for('views.login'))
    subjects = get_user_subjects(user_id)
    timetable = query_db("""
        SELECT ts.*, s.name as subject_name, s.color as subject_color, s.code as subject_code
        FROM timetable_slots ts
        JOIN subjects s ON ts.subject_id = s.id
        WHERE ts.user_id = ?
        ORDER BY ts.day_of_week, ts.start_time
    """, (user_id,))
    
    exams = query_db("""
        SELECT e.*, s.name as subject_name, s.color as subject_color
        FROM exams e
        JOIN subjects s ON e.subject_id = s.id
        WHERE e.user_id = ?
        ORDER BY e.exam_date ASC
    """, (user_id,))
    
    return render_template('pages/calendar.html',
                           user=user,
                           subjects=subjects,
                           timetable=timetable,
                           exams=exams,
                           active_page='calendar')

@views_bp.route('/analytics')
@login_required
def analytics():
    user_id = get_current_user_id()
    user = get_current_user()
    if not user:
        session.clear()
        return redirect(url_for('views.login'))
    sync_completed_tasks_to_study_sessions(user_id)
    stats = get_overall_dashboard_stats(user_id)
    subjects = get_user_subjects(user_id)
    focus_today = get_today_focus_summary(user_id)
    recent_sessions = get_recent_sessions(user_id, limit=30)
    
    return render_template('pages/analytics.html',
                           user=user,
                           stats=stats,
                           subjects=subjects,
                           focus_today=focus_today,
                           recent_sessions=recent_sessions,
                           active_page='analytics')

@views_bp.route('/login')
def login():
    if session.get('user_id'):
        return redirect(url_for('views.index_view'))
    google_client_id = current_app.config.get('GOOGLE_CLIENT_ID', '')
    return render_template('pages/login.html', google_client_id=google_client_id)

@views_bp.route('/register')
def register():
    if session.get('user_id'):
        return redirect(url_for('views.index_view'))
    google_client_id = current_app.config.get('GOOGLE_CLIENT_ID', '')
    return render_template('pages/register.html', google_client_id=google_client_id)

@views_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('views.login'))
