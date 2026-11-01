# 🎓 Student Study Planner (StudyFlow)

A modern, full-stack, responsive **Student Study Planner** built with **Python (Flask)**, **SQLite**, and **Vanilla HTML5, CSS3, and JavaScript**.

---

## 🌟 Key Features

1. **📊 Intelligent Student Dashboard**
   - Study time metrics, streak counter, upcoming exams, today's lecture schedule, and fast-track tasks.
2. **📚 Courses & Syllabus Management**
   - Course cards with custom color themes, weekly study targets, and module completion checklists with live progress bars.
3. **📋 Tasks & Kanban Assignment Board**
   - 3-Column Kanban board (*To Do*, *In Progress*, *Completed*) with priority badges, deadlines, and course filtering.
4. **⏱️ Immersive Focus Room & Pomodoro Timer**
   - Animated circular SVG countdown timer (Pomodoro 25m, Short Break 5m, Long Break 15m, Custom), browser chime alerts, and direct session logging to SQLite.
5. **📅 Timetable & Exam Calendar**
   - Weekly lecture schedule grid (Monday to Friday) and exam countdown manager with syllabus notes and grade weights.
6. **📈 Deep Study Analytics**
   - Interactive charts powered by Chart.js (7-day study trend bar chart, course time distribution doughnut chart) and session logs table.
7. **🔐 User Authentication**
   - Secure login and registration with hashed passwords (`werkzeug.security`).

---

## 📂 Project Architecture

```text
StudentStudyPlanner/
├── run.py                       # Main application entry point
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables
├── README.md                    # Project documentation
│
├── 📁 database/                 # ==========================================
│   │                            # 💾 DATABASE LAYER
│   │                            # ==========================================
│   ├── db.py                    # SQLite connection & query helpers
│   ├── schema.sql               # Database schema (DDL)
│   ├── init_db.py               # Table initialization script
│   ├── seed.py                  # Demo data generator
│   └── study_planner.db         # SQLite database file
│
├── 📁 backend/                  # ==========================================
│   │                            # ⚙️ BACKEND LAYER (Flask Application)
│   │                            # ==========================================
│   ├── __init__.py              # Flask app factory
│   ├── config.py                # Environment configurations
│   ├── utils/                   # Helpers (auth, dates, formatters)
│   ├── services/                # Business logic & calculations
│   └── routes/                  # Modular REST APIs & page view routes
│
└── 📁 frontend/                 # ==========================================
    │                            # 🎨 FRONTEND LAYER
    │                            # ==========================================
    ├── 📁 templates/            # Jinja2 HTML views & layouts
    │   ├── layouts/             # Master templates (base.html, auth_base.html)
    │   ├── components/          # Reusable snippets (sidebar, header, modals)
    │   └── pages/               # Page views (dashboard, subjects, tasks, etc.)
    └── 📁 static/               # Static assets
        ├── 📁 css/              # Design system tokens, components, page styles
        └── 📁 js/               # API client, Pomodoro engine, Chart.js modules
```

---

## 🚀 Quick Start Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Initialize and Seed the Database
```bash
python database/seed.py
```
*(This sets up all tables and loads sample computer science courses, tasks, focus logs, and exam schedules so your dashboard looks vibrant immediately)*

### 3. Run the Application
```bash
python run.py
```

### 4. Open in Browser
Navigate to **`http://127.0.0.1:5000`** in your browser.

* Demo User Login (pre-seeded):
  - **Username:** `alex_student`
  - **Password:** `password123`
*(Or you can register a new account anytime!)*

---

## 🔐 Authentication & Sign-In Options

When you open the project at `http://127.0.0.1:5000`, login is required before accessing the study dashboard:

1. **Sign In with Gmail ID & Password:**
   - Enter your registered Gmail address (e.g. `yourname@gmail.com`) and your password.
   - If you are new, click **Create Account** to register with your Gmail ID and create your study profile.
   - Case-insensitive email and username login supported.

2. **Sign In with Google:**
   - Click the official **Sign in with Google** button.
   - Works with Google Identity Services (GSI).
   - If `GOOGLE_CLIENT_ID` is not yet configured, you can click **🔴 Google Demo** (`student.google@gmail.com`) for 1-click instant local testing.

### Setting up Real Google OAuth (Optional for Production):
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
2. Create an **OAuth 2.0 Client ID** (Application type: *Web application*).
3. Under **Authorized JavaScript origins**, add:
   - `http://127.0.0.1:5000`
   - `http://localhost:5000`
4. Copy your Client ID and add it into `.env`:
   ```env
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```
5. Restart `python run.py`. The official Google Sign-In prompt will authenticate directly with Google!

3. **Sign Out:**
   - Click **Sign Out** from the bottom of the sidebar or the top navbar at any time.

---

## 🛠️ API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/subjects` | Get all courses with study stats |
| `POST` | `/api/subjects` | Create a new course |
| `POST` | `/api/subjects/<id>/topics` | Add syllabus topic |
| `PUT` | `/api/subjects/topics/<id>/toggle`| Check/uncheck syllabus topic |
| `GET` | `/api/tasks` | Get tasks (supports `?subject_id=&grouped=true`) |
| `POST` | `/api/tasks` | Create task |
| `PATCH` | `/api/tasks/<id>/status` | Update task status (`todo`, `in_progress`, `completed`) |
| `POST` | `/api/timer/session` | Log completed study session |
| `GET` | `/api/analytics/weekly-trend` | Last 7 days study hours for Chart.js |
| `GET` | `/api/analytics/subject-distribution` | Course breakdown for Chart.js |
| `GET` | `/api/timetable` | Get weekly class schedule |
| `POST` | `/api/exams` | Schedule an exam |
