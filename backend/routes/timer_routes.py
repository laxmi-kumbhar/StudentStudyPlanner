from flask import Blueprint, request, jsonify
from backend.utils.auth_helpers import get_current_user_id
from backend.services.timer_service import (
    log_study_session, get_today_focus_summary, get_recent_sessions
)
from backend.services.task_service import sync_completed_tasks_to_study_sessions

timer_bp = Blueprint('timer', __name__, url_prefix='/api/timer')

@timer_bp.route('/session', methods=['POST'])
def save_session():
    user_id = get_current_user_id()
    data = request.get_json() or {}
    
    subject_id = data.get('subject_id')
    duration_minutes = int(data.get('duration_minutes', 25))
    session_type = data.get('session_type', 'pomodoro')
    notes = data.get('notes', '').strip()
    task_id = data.get('task_id')
    
    if duration_minutes <= 0:
        return jsonify({"success": False, "error": "Duration must be greater than 0."}), 400
        
    session_id = log_study_session(user_id, subject_id, duration_minutes, session_type, notes, task_id)
    summary = get_today_focus_summary(user_id)
    
    return jsonify({
        "success": True, 
        "message": "Focus session logged successfully!", 
        "session_id": session_id,
        "summary": summary
    }), 201

@timer_bp.route('/today', methods=['GET'])
def get_today():
    user_id = get_current_user_id()
    summary = get_today_focus_summary(user_id)
    return jsonify({"success": True, "data": summary})

@timer_bp.route('/history', methods=['GET'])
def get_history():
    user_id = get_current_user_id()
    limit = request.args.get('limit', 20, type=int)
    sync_completed_tasks_to_study_sessions(user_id)
    sessions = get_recent_sessions(user_id, limit=limit)
    return jsonify({"success": True, "sessions": sessions})
