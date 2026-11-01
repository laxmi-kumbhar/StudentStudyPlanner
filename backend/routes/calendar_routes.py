from flask import Blueprint, request, jsonify
from backend.utils.auth_helpers import get_current_user_id
from database.db import query_db, execute_db

calendar_bp = Blueprint('calendar', __name__, url_prefix='/api')

# ================= TIMETABLE =================
@calendar_bp.route('/timetable', methods=['GET'])
def get_timetable():
    user_id = get_current_user_id()
    slots = query_db("""
        SELECT ts.*, s.name as subject_name, s.color as subject_color, s.code as subject_code
        FROM timetable_slots ts
        JOIN subjects s ON ts.subject_id = s.id
        WHERE ts.user_id = ?
        ORDER BY ts.day_of_week, ts.start_time
    """, (user_id,))
    return jsonify({"success": True, "timetable": slots})

@calendar_bp.route('/timetable', methods=['POST'])
def add_timetable_slot():
    user_id = get_current_user_id()
    data = request.get_json() or {}
    
    subject_id = data.get('subject_id')
    day_of_week = int(data.get('day_of_week', 0))
    start_time = data.get('start_time', '').strip()
    end_time = data.get('end_time', '').strip()
    location = data.get('location', '').strip()
    
    if not subject_id or not start_time or not end_time:
        return jsonify({"success": False, "error": "Subject, start time, and end time are required."}), 400
        
    res = execute_db("""
        INSERT INTO timetable_slots (user_id, subject_id, day_of_week, start_time, end_time, location)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, subject_id, day_of_week, start_time, end_time, location))
    
    return jsonify({"success": True, "message": "Class schedule added!", "slot_id": res['lastrowid']}), 201

@calendar_bp.route('/timetable/<int:slot_id>', methods=['PUT', 'PATCH'])
def update_timetable_slot(slot_id):
    user_id = get_current_user_id()
    data = request.get_json() or {}
    
    subject_id = data.get('subject_id')
    day_of_week = int(data.get('day_of_week', 0))
    start_time = data.get('start_time', '').strip()
    end_time = data.get('end_time', '').strip()
    location = data.get('location', '').strip()
    
    if not subject_id or not start_time or not end_time:
        return jsonify({"success": False, "error": "Subject, start time, and end time are required."}), 400
        
    execute_db("""
        UPDATE timetable_slots
        SET subject_id = ?, day_of_week = ?, start_time = ?, end_time = ?, location = ?
        WHERE id = ? AND user_id = ?
    """, (subject_id, day_of_week, start_time, end_time, location, slot_id, user_id))
    
    return jsonify({"success": True, "message": "Class schedule updated!"})

@calendar_bp.route('/timetable/<int:slot_id>', methods=['DELETE'])
def delete_timetable_slot(slot_id):
    user_id = get_current_user_id()
    execute_db("DELETE FROM timetable_slots WHERE id = ? AND user_id = ?", (slot_id, user_id))
    return jsonify({"success": True, "message": "Class schedule removed!"})

# ================= EXAMS & DEADLINES =================
@calendar_bp.route('/exams', methods=['GET'])
def get_exams():
    user_id = get_current_user_id()
    exams = query_db("""
        SELECT e.*, s.name as subject_name, s.color as subject_color
        FROM exams e
        JOIN subjects s ON e.subject_id = s.id
        WHERE e.user_id = ?
        ORDER BY e.exam_date ASC
    """, (user_id,))
    return jsonify({"success": True, "exams": exams})

@calendar_bp.route('/exams', methods=['POST'])
def add_exam():
    user_id = get_current_user_id()
    data = request.get_json() or {}
    
    subject_id = data.get('subject_id')
    title = data.get('title', '').strip()
    exam_date = data.get('exam_date')
    room_or_link = data.get('room_or_link', '').strip()
    notes = data.get('notes', '').strip()
    weight = float(data.get('weight_percentage', 0))
    
    if not subject_id or not title or not exam_date:
        return jsonify({"success": False, "error": "Subject, title, and exam date are required."}), 400
        
    res = execute_db("""
        INSERT INTO exams (user_id, subject_id, title, exam_date, room_or_link, notes, weight_percentage)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, subject_id, title, exam_date, room_or_link, notes, weight))
    
    return jsonify({"success": True, "message": "Exam scheduled successfully!", "exam_id": res['lastrowid']}), 201

@calendar_bp.route('/exams/<int:exam_id>', methods=['PUT', 'PATCH'])
def update_exam(exam_id):
    user_id = get_current_user_id()
    data = request.get_json() or {}
    
    subject_id = data.get('subject_id')
    title = data.get('title', '').strip()
    exam_date = data.get('exam_date')
    room_or_link = data.get('room_or_link', '').strip()
    notes = data.get('notes', '').strip()
    weight = float(data.get('weight_percentage', 0))
    
    if not subject_id or not title or not exam_date:
        return jsonify({"success": False, "error": "Subject, title, and exam date are required."}), 400
        
    execute_db("""
        UPDATE exams
        SET subject_id = ?, title = ?, exam_date = ?, room_or_link = ?, notes = ?, weight_percentage = ?
        WHERE id = ? AND user_id = ?
    """, (subject_id, title, exam_date, room_or_link, notes, weight, exam_id, user_id))
    
    return jsonify({"success": True, "message": "Exam updated!"})

@calendar_bp.route('/exams/<int:exam_id>', methods=['DELETE'])
def delete_exam(exam_id):
    user_id = get_current_user_id()
    execute_db("DELETE FROM exams WHERE id = ? AND user_id = ?", (exam_id, user_id))
    return jsonify({"success": True, "message": "Exam deleted!"})
