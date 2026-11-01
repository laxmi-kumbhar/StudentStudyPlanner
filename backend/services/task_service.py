from datetime import datetime
from database.db import query_db, execute_db
from backend.utils.date_helpers import format_relative_date

def get_tasks(user_id: int, subject_id=None, status=None, priority=None):
    """Retrieve tasks with subject metadata and human-readable due date."""
    query = """
        SELECT t.*, s.name as subject_name, s.color as subject_color, s.code as subject_code
        FROM tasks t
        LEFT JOIN subjects s ON t.subject_id = s.id
        WHERE t.user_id = ?
    """
    params = [user_id]
    
    if subject_id:
        query += " AND t.subject_id = ?"
        params.append(subject_id)
    if status:
        query += " AND t.status = ?"
        params.append(status)
    if priority:
        query += " AND t.priority = ?"
        params.append(priority)
        
    query += """
        ORDER BY 
            CASE t.status 
                WHEN 'in_progress' THEN 1 
                WHEN 'todo' THEN 2 
                ELSE 3 
            END,
            CASE 
                WHEN t.due_date IS NULL THEN 1 
                ELSE 0 
            END,
            t.due_date ASC,
            t.id DESC
    """
    
    tasks = query_db(query, tuple(params))
    for t in tasks:
        t['relative_due_date'] = format_relative_date(t['due_date'])
    return tasks

def get_tasks_grouped(user_id: int, subject_id=None):
    """Retrieve tasks grouped into Kanban columns: todo, in_progress, completed."""
    all_tasks = get_tasks(user_id, subject_id)
    grouped = {
        'todo': [],
        'in_progress': [],
        'completed': []
    }
    for t in all_tasks:
        stat = t.get('status', 'todo')
        if stat in grouped:
            grouped[stat].append(t)
        else:
            grouped['todo'].append(t)
    return grouped

def create_task(user_id: int, title: str, description: str, subject_id: int, priority: str, due_date: str, estimated_minutes: int):
    """Create a new task."""
    res = execute_db("""
        INSERT INTO tasks (user_id, subject_id, title, description, priority, status, due_date, estimated_minutes)
        VALUES (?, ?, ?, ?, ?, 'todo', ?, ?)
    """, (user_id, subject_id, title, description, priority, due_date, estimated_minutes))
    return res['lastrowid']

def update_task(user_id: int, task_id: int, title: str, description: str, subject_id: int, priority: str, due_date: str, estimated_minutes: int):
    """Update task details."""
    return execute_db("""
        UPDATE tasks 
        SET title = ?, description = ?, subject_id = ?, priority = ?, due_date = ?, estimated_minutes = ?
        WHERE id = ? AND user_id = ?
    """, (title, description, subject_id, priority, due_date, estimated_minutes, task_id, user_id))

def update_task_status(user_id: int, task_id: int, new_status: str):
    """Update task status (e.g. from 'todo' to 'in_progress' or 'completed').
    When marked 'completed', automatically records a completed focus session in study_sessions.
    If moved back to 'todo' or 'in_progress', removes the auto-logged focus session.
    """
    task = query_db("SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id), one=True)
    if not task:
        return None

    completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if new_status == 'completed' else None
    res = execute_db("""
        UPDATE tasks 
        SET status = ?, completed_at = ?
        WHERE id = ? AND user_id = ?
    """, (new_status, completed_at, task_id, user_id))

    if new_status == 'completed':
        # Check if focus session log already exists for this task
        existing = query_db("""
            SELECT id FROM study_sessions WHERE task_id = ? AND user_id = ?
        """, (task_id, user_id), one=True)

        if not existing:
            duration = int(task['estimated_minutes'] or 30)
            if duration <= 0:
                duration = 30
            task_title = task['title']
            notes = f"Completed Task: {task_title}"
            execute_db("""
                INSERT INTO study_sessions (user_id, subject_id, task_id, duration_minutes, session_type, notes, created_at)
                VALUES (?, ?, ?, ?, 'custom', ?, ?)
            """, (user_id, task['subject_id'], task_id, duration, notes, completed_at))
    else:
        # Reverted back from completed: remove auto-logged focus session for this task
        execute_db("""
            DELETE FROM study_sessions WHERE task_id = ? AND user_id = ?
        """, (task_id, user_id))

    return res

def delete_task(user_id: int, task_id: int):
    """Delete a task and its associated auto-logged study session."""
    execute_db("DELETE FROM study_sessions WHERE task_id = ? AND user_id = ?", (task_id, user_id))
    return execute_db("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))

def sync_completed_tasks_to_study_sessions(user_id: int):
    """Backfill / synchronize all completed tasks that don't have a focus session log yet."""
    unlogged_completed_tasks = query_db("""
        SELECT t.* FROM tasks t
        LEFT JOIN study_sessions ss ON t.id = ss.task_id AND ss.user_id = t.user_id
        WHERE t.user_id = ? AND t.status = 'completed' AND ss.id IS NULL
    """, (user_id,))

    for t in unlogged_completed_tasks:
        duration = int(t['estimated_minutes'] or 30)
        if duration <= 0:
            duration = 30
        task_title = t['title']
        notes = f"Completed Task: {task_title}"
        created_at = t['completed_at'] or t['created_at'] or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        execute_db("""
            INSERT INTO study_sessions (user_id, subject_id, task_id, duration_minutes, session_type, notes, created_at)
            VALUES (?, ?, ?, ?, 'custom', ?, ?)
        """, (user_id, t['subject_id'], t['id'], duration, notes, created_at))

