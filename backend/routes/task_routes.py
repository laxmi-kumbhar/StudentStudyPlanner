from flask import Blueprint, request, jsonify
from backend.utils.auth_helpers import get_current_user_id
from backend.services.task_service import (
    get_tasks, get_tasks_grouped, create_task, update_task, update_task_status, delete_task
)

task_bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')

@task_bp.route('', methods=['GET'])
def list_tasks():
    user_id = get_current_user_id()
    subject_id = request.args.get('subject_id', type=int)
    status = request.args.get('status')
    priority = request.args.get('priority')
    grouped = request.args.get('grouped', 'false').lower() == 'true'
    
    if grouped:
        tasks = get_tasks_grouped(user_id, subject_id)
    else:
        tasks = get_tasks(user_id, subject_id, status, priority)
        
    return jsonify({"success": True, "tasks": tasks})

@task_bp.route('', methods=['POST'])
def add_task():
    user_id = get_current_user_id()
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    subject_id = data.get('subject_id')
    priority = data.get('priority', 'medium')
    due_date = data.get('due_date')
    estimated_minutes = int(data.get('estimated_minutes', 30))
    
    if not title:
        return jsonify({"success": False, "error": "Task title is required."}), 400
        
    task_id = create_task(user_id, title, description, subject_id, priority, due_date, estimated_minutes)
    return jsonify({"success": True, "message": "Task created successfully!", "task_id": task_id}), 201

@task_bp.route('/<int:task_id>', methods=['PUT'])
def edit_task(task_id):
    user_id = get_current_user_id()
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    subject_id = data.get('subject_id')
    priority = data.get('priority', 'medium')
    due_date = data.get('due_date')
    estimated_minutes = int(data.get('estimated_minutes', 30))
    
    if not title:
        return jsonify({"success": False, "error": "Task title is required."}), 400
        
    update_task(user_id, task_id, title, description, subject_id, priority, due_date, estimated_minutes)
    return jsonify({"success": True, "message": "Task updated successfully!"})

@task_bp.route('/<int:task_id>/status', methods=['PATCH', 'PUT'])
def change_status(task_id):
    user_id = get_current_user_id()
    data = request.get_json() or {}
    new_status = data.get('status')
    
    if new_status not in ['todo', 'in_progress', 'completed']:
        return jsonify({"success": False, "error": "Invalid task status."}), 400
        
    update_task_status(user_id, task_id, new_status)
    return jsonify({"success": True, "message": f"Status changed to {new_status}"})

@task_bp.route('/<int:task_id>', methods=['DELETE'])
def remove_task(task_id):
    user_id = get_current_user_id()
    delete_task(user_id, task_id)
    return jsonify({"success": True, "message": "Task deleted successfully!"})
