from database.db import query_db, execute_db

def get_user_subjects(user_id: int):
    """Retrieve all subjects for a user with syllabus completion percentage and study hours."""
    subjects = query_db("""
        SELECT s.*, 
            COUNT(t.id) as total_topics,
            SUM(CASE WHEN t.is_completed = 1 THEN 1 ELSE 0 END) as completed_topics,
            COALESCE((
                SELECT SUM(ss.duration_minutes) 
                FROM study_sessions ss 
                WHERE ss.subject_id = s.id
            ), 0) as total_study_minutes
        FROM subjects s
        LEFT JOIN topics t ON s.id = t.subject_id
        WHERE s.user_id = ?
        GROUP BY s.id
        ORDER BY s.name ASC
    """, (user_id,))
    
    for subj in subjects:
        total = subj['total_topics'] or 0
        comp = subj['completed_topics'] or 0
        subj['progress_pct'] = round((comp / total * 100)) if total > 0 else 0
        subj['total_study_hours'] = round(subj['total_study_minutes'] / 60.0, 1)
    
    return subjects

def get_subject_details(user_id: int, subject_id: int):
    """Retrieve subject details along with all syllabus topics and recent tasks."""
    subject = query_db("""
        SELECT * FROM subjects WHERE id = ? AND user_id = ?
    """, (subject_id, user_id), one=True)
    
    if not subject:
        return None
    
    topics = query_db("""
        SELECT * FROM topics WHERE subject_id = ? AND user_id = ? ORDER BY id ASC
    """, (subject_id, user_id))
    
    tasks = query_db("""
        SELECT * FROM tasks WHERE subject_id = ? AND user_id = ? ORDER BY due_date ASC
    """, (subject_id, user_id))
    
    total_study = query_db("""
        SELECT SUM(duration_minutes) as total_minutes FROM study_sessions WHERE subject_id = ? AND user_id = ?
    """, (subject_id, user_id), one=True)
    
    total_mins = total_study['total_minutes'] if total_study and total_study['total_minutes'] else 0
    
    subject['topics'] = topics
    subject['tasks'] = tasks
    subject['total_study_minutes'] = total_mins
    subject['total_study_hours'] = round(total_mins / 60.0, 1)
    
    total_topics = len(topics)
    completed_topics = sum(1 for t in topics if t['is_completed'] == 1)
    subject['progress_pct'] = round((completed_topics / total_topics * 100)) if total_topics > 0 else 0
    
    return subject

def create_subject(user_id: int, name: str, code: str, color: str, icon: str, target_hours: float):
    """Create a new subject."""
    res = execute_db("""
        INSERT INTO subjects (user_id, name, code, color, icon, target_hours_per_week)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, name, code, color, icon, target_hours))
    return res['lastrowid']

def update_subject(user_id: int, subject_id: int, name: str, code: str, color: str, icon: str, target_hours: float):
    """Update subject info."""
    return execute_db("""
        UPDATE subjects 
        SET name = ?, code = ?, color = ?, icon = ?, target_hours_per_week = ?
        WHERE id = ? AND user_id = ?
    """, (name, code, color, icon, target_hours, subject_id, user_id))

def delete_subject(user_id: int, subject_id: int):
    """Delete a subject and cascade delete associated records."""
    return execute_db("DELETE FROM subjects WHERE id = ? AND user_id = ?", (subject_id, user_id))

def add_topic(user_id: int, subject_id: int, title: str):
    """Add a topic to subject syllabus."""
    res = execute_db("""
        INSERT INTO topics (subject_id, user_id, title, is_completed)
        VALUES (?, ?, ?, 0)
    """, (subject_id, user_id, title))
    return res['lastrowid']

def toggle_topic(user_id: int, topic_id: int):
    """Toggle topic completed state."""
    topic = query_db("SELECT is_completed FROM topics WHERE id = ? AND user_id = ?", (topic_id, user_id), one=True)
    if not topic:
        return None
    new_status = 0 if topic['is_completed'] == 1 else 1
    execute_db("UPDATE topics SET is_completed = ? WHERE id = ? AND user_id = ?", (new_status, topic_id, user_id))
    return new_status

def delete_topic(user_id: int, topic_id: int):
    """Delete topic."""
    return execute_db("DELETE FROM topics WHERE id = ? AND user_id = ?", (topic_id, user_id))
