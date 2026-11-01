import sys
import os
import sqlite3
from datetime import datetime, timedelta, date
from werkzeug.security import generate_password_hash

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.db import get_db_path, init_db

def seed_database():
    print("Resetting and initializing database...")
    init_db()
    
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")
    
    # 1. Create Demo User
    demo_password_hash = generate_password_hash("password123")
    cur.execute("""
        INSERT INTO users (username, email, password_hash, avatar_color, daily_goal_minutes)
        VALUES (?, ?, ?, ?, ?)
    """, ("alex_student", "alex@study.edu", demo_password_hash, "#6366f1", 180))
    user_id = cur.lastrowid
    print(f"Created demo user: alex_student (ID: {user_id})")

    # 2. Create Subjects
    subjects_data = [
        ("Data Structures & Algorithms", "CS-201", "#6366f1", "code-2", 8.0),
        ("Database Management Systems", "CS-204", "#06b6d4", "database", 6.0),
        ("Machine Learning Foundations", "AI-301", "#ec4899", "cpu", 7.0),
        ("Operating Systems & Architecture", "CS-208", "#10b981", "server", 5.0),
        ("Computer Networks & Protocols", "CS-210", "#f59e0b", "globe", 4.0),
    ]
    
    subject_ids = {}
    for name, code, color, icon, target_hours in subjects_data:
        cur.execute("""
            INSERT INTO subjects (user_id, name, code, color, icon, target_hours_per_week)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, name, code, color, icon, target_hours))
        subject_ids[code] = cur.lastrowid
    
    print(f"Created {len(subject_ids)} subjects.")

    # 3. Create Syllabus Topics per Subject
    topics_data = [
        # CS-201
        (subject_ids["CS-201"], "Arrays, Linked Lists, and Stacks", 1),
        (subject_ids["CS-201"], "Binary Search Trees & AVL Trees", 1),
        (subject_ids["CS-201"], "Graph Traversals (BFS & DFS)", 1),
        (subject_ids["CS-201"], "Dynamic Programming & Memoization", 0),
        (subject_ids["CS-201"], "Dijkstra & Minimum Spanning Trees", 0),
        # CS-204
        (subject_ids["CS-204"], "Relational Algebra & Normalization (1NF, 2NF, 3NF, BCNF)", 1),
        (subject_ids["CS-204"], "Complex SQL Joins, Subqueries & Window Functions", 1),
        (subject_ids["CS-204"], "Indexing, B-Trees & Query Optimization", 0),
        (subject_ids["CS-204"], "ACID Transactions & Concurrency Control", 0),
        # AI-301
        (subject_ids["AI-301"], "Linear Regression & Gradient Descent", 1),
        (subject_ids["AI-301"], "Logistic Regression & Classification Metrics", 1),
        (subject_ids["AI-301"], "Neural Networks & Backpropagation", 0),
        (subject_ids["AI-301"], "Convolutional Neural Networks (CNNs)", 0),
        # CS-208
        (subject_ids["CS-208"], "Processes, Threads & Concurrency", 1),
        (subject_ids["CS-208"], "CPU Scheduling Algorithms", 1),
        (subject_ids["CS-208"], "Virtual Memory Management & Paging", 0),
        (subject_ids["CS-208"], "File System Implementation", 0),
        # CS-210
        (subject_ids["CS-210"], "OSI & TCP/IP 5-Layer Reference Models", 1),
        (subject_ids["CS-210"], "Subnetting, CIDR & IP Routing (OSPF/BGP)", 0),
        (subject_ids["CS-210"], "Transport Protocols (TCP 3-Way Handshake vs UDP)", 1),
        (subject_ids["CS-210"], "DNS, HTTP/2, HTTPS & TLS Handshake", 0),
    ]

    for subj_id, title, is_comp in topics_data:
        cur.execute("""
            INSERT INTO topics (subject_id, user_id, title, is_completed)
            VALUES (?, ?, ?, ?)
        """, (subj_id, user_id, title, is_comp))

    print(f"Created {len(topics_data)} syllabus topics.")

    # 4. Create Tasks / Assignments (Kanban)
    today = date.today()
    tasks_data = [
        # To Do
        (subject_ids["CS-201"], "Implement Red-Black Tree in C++", "Complete assignment 3 with rotation unit tests", "urgent", "todo", today + timedelta(days=2), 90),
        (subject_ids["AI-301"], "Train CNN Model on CIFAR-10", "Implement PyTorch baseline notebook with data augmentation", "high", "todo", today + timedelta(days=4), 120),
        (subject_ids["CS-210"], "Packet Analysis with Wireshark", "Capture and analyze TCP stream and handshake packets", "medium", "todo", today + timedelta(days=6), 45),
        # In Progress
        (subject_ids["CS-204"], "Design E-Commerce DB Schema", "Draft ER diagram and write DDL scripts for 3NF schema", "high", "in_progress", today + timedelta(days=1), 60),
        (subject_ids["CS-208"], "Solve Deadlock Simulation Problems", "Practice banker's algorithm and resource allocation graphs", "medium", "in_progress", today + timedelta(days=3), 45),
        # Completed
        (subject_ids["CS-201"], "Solve 10 LeetCode Medium Graphs", "Practiced BFS, DFS, and topological sort questions", "high", "completed", today - timedelta(days=1), 120),
        (subject_ids["CS-204"], "SQL Window Functions Quiz Prep", "Reviewed rank, dense_rank, and partition by syntax", "low", "completed", today - timedelta(days=2), 40),
        (subject_ids["AI-301"], "Review Linear Algebra & PCA Notes", "Matrix decompositions and eigenvalues review", "medium", "completed", today - timedelta(days=3), 60),
    ]

    for subj_id, title, desc, prio, stat, due, est in tasks_data:
        comp_at = (datetime.now() - timedelta(days=1)) if stat == 'completed' else None
        cur.execute("""
            INSERT INTO tasks (user_id, subject_id, title, description, priority, status, due_date, estimated_minutes, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, subj_id, title, desc, prio, stat, due.isoformat(), est, comp_at))

    print(f"Created {len(tasks_data)} tasks.")

    # 5. Create Study Sessions (Focus Logs over the past 7 days)
    sessions_data = [
        (subject_ids["CS-201"], 50, "pomodoro", "Graph traversals and cycle detection", 6),
        (subject_ids["CS-201"], 25, "pomodoro", "DFS recursion stack debugging", 6),
        (subject_ids["CS-204"], 60, "stopwatch", "SQL indexing benchmark queries", 5),
        (subject_ids["AI-301"], 45, "pomodoro", "Gradient descent derivations and coding", 4),
        (subject_ids["AI-301"], 50, "pomodoro", "Backpropagation equations review", 4),
        (subject_ids["CS-208"], 40, "custom", "CPU scheduling Gantt charts", 3),
        (subject_ids["CS-210"], 50, "pomodoro", "Subnetting calculations practice", 2),
        (subject_ids["CS-201"], 75, "stopwatch", "Dynamic programming memoization table", 1),
        (subject_ids["CS-204"], 50, "pomodoro", "Relational calculus & schema normalization", 1),
        (subject_ids["AI-301"], 45, "pomodoro", "Logistic regression loss curve analysis", 0),
        (subject_ids["CS-208"], 30, "pomodoro", "Memory paging & TLB cache lookups", 0),
    ]

    for subj_id, dur, stype, note, days_ago in sessions_data:
        session_time = datetime.now() - timedelta(days=days_ago, hours=2)
        cur.execute("""
            INSERT INTO study_sessions (user_id, subject_id, duration_minutes, session_type, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, subj_id, dur, stype, note, session_time.strftime("%Y-%m-%d %H:%M:%S")))

    print(f"Created {len(sessions_data)} study session logs.")

    # 6. Weekly Timetable Slots (0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday)
    timetable_data = [
        (subject_ids["CS-201"], 0, "09:00", "10:30", "Hall A - Room 201"), # Mon
        (subject_ids["CS-204"], 0, "11:00", "12:30", "Lab 3"),             # Mon
        (subject_ids["AI-301"], 1, "10:00", "11:30", "Tech Amphitheater"),  # Tue
        (subject_ids["CS-208"], 1, "14:00", "15:30", "Room 105"),          # Tue
        (subject_ids["CS-201"], 2, "09:00", "10:30", "Hall A - Room 201"), # Wed
        (subject_ids["CS-210"], 2, "13:00", "14:30", "Networking Lab 2"),  # Wed
        (subject_ids["CS-204"], 3, "11:00", "12:30", "Lab 3"),             # Thu
        (subject_ids["AI-301"], 3, "14:00", "15:30", "Tech Amphitheater"),  # Thu
        (subject_ids["CS-208"], 4, "10:00", "11:30", "Room 105"),          # Fri
        (subject_ids["CS-210"], 4, "13:00", "14:30", "Networking Lab 2"),  # Fri
    ]

    for subj_id, day, st, et, loc in timetable_data:
        cur.execute("""
            INSERT INTO timetable_slots (user_id, subject_id, day_of_week, start_time, end_time, location)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, subj_id, day, st, et, loc))

    print(f"Created {len(timetable_data)} timetable entries.")

    # 7. Exams & Deadlines
    exams_data = [
        (subject_ids["CS-201"], "Midterm Exam: Algorithms & Data Structures", datetime.now() + timedelta(days=8, hours=10), "Exam Hall 1", "Comprehensive: Arrays to Graph BFS/DFS", 30.0),
        (subject_ids["CS-204"], "Database Management Project Submission & Viva", datetime.now() + timedelta(days=14, hours=14), "CS Lab 3", "Submit report and demo SQLite schema", 25.0),
        (subject_ids["AI-301"], "Machine Learning Quiz 2", datetime.now() + timedelta(days=19, hours=9), "Auditorium", "Linear/Logistic Regression & Neural Nets", 15.0),
        (subject_ids["CS-208"], "Operating Systems Final Exam", datetime.now() + timedelta(days=28, hours=11), "Main Hall B", "All chapters: Processes, Paging, File Systems", 40.0),
    ]

    for subj_id, title, ex_date, room, notes, weight in exams_data:
        cur.execute("""
            INSERT INTO exams (user_id, subject_id, title, exam_date, room_or_link, notes, weight_percentage)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, subj_id, title, ex_date.strftime("%Y-%m-%d %H:%M:%S"), room, notes, weight))

    print(f"Created {len(exams_data)} exams & deadlines.")

    conn.commit()
    conn.close()
    print("Database seeding completed successfully!")

if __name__ == '__main__':
    seed_database()
