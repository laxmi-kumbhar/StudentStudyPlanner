from flask import Blueprint, jsonify
from backend.utils.auth_helpers import get_current_user_id
from backend.services.analytics_service import (
    get_overall_dashboard_stats, get_weekly_study_trend, get_subject_time_distribution,
    get_user_badges
)
from backend.services.task_service import sync_completed_tasks_to_study_sessions

analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')

@analytics_bp.route('/overview', methods=['GET'])
def overview():
    user_id = get_current_user_id()
    sync_completed_tasks_to_study_sessions(user_id)
    stats = get_overall_dashboard_stats(user_id)
    return jsonify({"success": True, "stats": stats})

@analytics_bp.route('/weekly-trend', methods=['GET'])
def weekly_trend():
    user_id = get_current_user_id()
    sync_completed_tasks_to_study_sessions(user_id)
    data = get_weekly_study_trend(user_id)
    return jsonify({"success": True, "data": data})

@analytics_bp.route('/subject-distribution', methods=['GET'])
def subject_distribution():
    user_id = get_current_user_id()
    sync_completed_tasks_to_study_sessions(user_id)
    data = get_subject_time_distribution(user_id)
    return jsonify({"success": True, "data": data})

@analytics_bp.route('/badges', methods=['GET'])
def badges():
    user_id = get_current_user_id()
    badge_list = get_user_badges(user_id)
    return jsonify({"success": True, "badges": badge_list})
