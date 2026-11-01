from flask import Blueprint, request, jsonify
from backend.utils.auth_helpers import get_current_user_id
from backend.services.subject_service import (
    get_user_subjects, get_subject_details, create_subject, 
    update_subject, delete_subject, add_topic, toggle_topic, delete_topic
)

subject_bp = Blueprint('subjects', __name__, url_prefix='/api/subjects')

@subject_bp.route('', methods=['GET'])
def list_subjects():
    user_id = get_current_user_id()
    subjects = get_user_subjects(user_id)
    return jsonify({"success": True, "subjects": subjects})

@subject_bp.route('', methods=['POST'])
def add_new_subject():
    user_id = get_current_user_id()
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    code = data.get('code', '').strip()
    color = data.get('color', '#6366f1')
    icon = data.get('icon', 'book')
    target_hours = float(data.get('target_hours_per_week', 5.0))
    
    if not name:
        return jsonify({"success": False, "error": "Subject name is required."}), 400
        
    subject_id = create_subject(user_id, name, code, color, icon, target_hours)
    return jsonify({"success": True, "message": "Subject created successfully!", "subject_id": subject_id}), 201

@subject_bp.route('/<int:subject_id>', methods=['GET'])
def get_one_subject(subject_id):
    user_id = get_current_user_id()
    subj = get_subject_details(user_id, subject_id)
    if not subj:
        return jsonify({"success": False, "error": "Subject not found."}), 404
    return jsonify({"success": True, "subject": subj})

@subject_bp.route('/<int:subject_id>', methods=['PUT'])
def edit_subject(subject_id):
    user_id = get_current_user_id()
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    code = data.get('code', '').strip()
    color = data.get('color', '#6366f1')
    icon = data.get('icon', 'book')
    target_hours = float(data.get('target_hours_per_week', 5.0))
    
    if not name:
        return jsonify({"success": False, "error": "Subject name is required."}), 400
        
    update_subject(user_id, subject_id, name, code, color, icon, target_hours)
    return jsonify({"success": True, "message": "Subject updated successfully!"})

@subject_bp.route('/<int:subject_id>', methods=['DELETE'])
def remove_subject(subject_id):
    user_id = get_current_user_id()
    delete_subject(user_id, subject_id)
    return jsonify({"success": True, "message": "Subject deleted successfully!"})

@subject_bp.route('/<int:subject_id>/topics', methods=['POST'])
def add_subject_topic(subject_id):
    user_id = get_current_user_id()
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    if not title:
        return jsonify({"success": False, "error": "Topic title is required."}), 400
    
    topic_id = add_topic(user_id, subject_id, title)
    return jsonify({"success": True, "message": "Topic added!", "topic_id": topic_id}), 201

@subject_bp.route('/topics/<int:topic_id>/toggle', methods=['PUT'])
def toggle_subject_topic(topic_id):
    user_id = get_current_user_id()
    new_status = toggle_topic(user_id, topic_id)
    if new_status is None:
        return jsonify({"success": False, "error": "Topic not found."}), 404
    return jsonify({"success": True, "is_completed": new_status})

@subject_bp.route('/topics/<int:topic_id>', methods=['DELETE'])
def remove_topic(topic_id):
    user_id = get_current_user_id()
    delete_topic(user_id, topic_id)
    return jsonify({"success": True, "message": "Topic deleted successfully!"})
