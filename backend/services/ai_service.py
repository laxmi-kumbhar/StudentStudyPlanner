import os
import re
import json
import urllib.request
import urllib.error
from datetime import datetime, date, timedelta
from database.db import query_db
from backend.services.analytics_service import calculate_study_streak

# ---------------------------------------------------------------------------
# Manual .env Loader & Key Persister (Zero external dependencies)
# ---------------------------------------------------------------------------
def _get_env_file_path():
    """Return the absolute path to the project root .env file."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.env')

def _load_env_file():
    """Load key-value pairs from .env if present into os.environ."""
    env_path = _get_env_file_path()
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k:
                            os.environ[k] = v
        except Exception:
            pass

_load_env_file()

def save_ai_api_key(provider: str, api_key: str):
    """Save API key to os.environ and persist to .env file."""
    p_lower = provider.lower().strip()
    key_mapping = {
        "gemini": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
        "openai": "OPENAI_API_KEY",
        "openrouter": "OPENROUTER_API_KEY"
    }

    if p_lower == "builtin":
        os.environ["AI_ACTIVE_PROVIDER"] = "builtin"
        env_var_name = None
    else:
        env_var_name = key_mapping.get(p_lower)
        if not env_var_name:
            raise ValueError(f"Unknown provider '{provider}'. Must be builtin, gemini, groq, openai, or openrouter.")
        
        api_key = api_key.strip()
        if not api_key:
            # Clear key
            os.environ.pop(env_var_name, None)
        else:
            os.environ[env_var_name] = api_key
            os.environ["AI_ACTIVE_PROVIDER"] = p_lower

    # Read existing .env lines
    env_path = _get_env_file_path()
    lines = []
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception:
            lines = []

    # Replace or append key
    found_key = False
    found_provider = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if env_var_name and stripped.startswith(f"{env_var_name}="):
            if api_key:
                new_lines.append(f"{env_var_name}={api_key}\n")
            found_key = True
        elif stripped.startswith("AI_ACTIVE_PROVIDER="):
            new_lines.append(f"AI_ACTIVE_PROVIDER={p_lower}\n")
            found_provider = True
        else:
            new_lines.append(line)

    if env_var_name and api_key and not found_key:
        new_lines.append(f"{env_var_name}={api_key}\n")
    if not found_provider:
        new_lines.append(f"AI_ACTIVE_PROVIDER={p_lower}\n")

    try:
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
    except Exception as e:
        print(f"Could not persist to .env: {e}")

    return get_ai_config_status()

def get_ai_config_status():
    """Return status of configured AI providers."""
    _load_env_file()
    has_gemini = bool(os.environ.get("GEMINI_API_KEY"))
    has_groq = bool(os.environ.get("GROQ_API_KEY"))
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))
    active = os.environ.get("AI_ACTIVE_PROVIDER", "").lower()

    if not active:
        if has_gemini:
            active = "gemini"
        elif has_groq:
            active = "groq"
        elif has_openai:
            active = "openai"
        else:
            active = "builtin"

    display_names = {
        "gemini": "Google Gemini (Active)",
        "groq": "Groq Llama 3.3 (Active)",
        "openai": "OpenAI ChatGPT (Active)",
        "builtin": "Built-in Conversational Assistant (Active)"
    }

    return {
        "has_gemini": has_gemini,
        "has_groq": has_groq,
        "has_openai": has_openai,
        "active_provider": active,
        "active_display": display_names.get(active, "Built-in Conversational Assistant")
    }


# ---------------------------------------------------------------------------
# Student Context Retrieval
# ---------------------------------------------------------------------------
def get_student_study_context(user_id: int):
    """Collect current student study context (subjects, tasks, exams, stats)."""
    user = query_db("SELECT id, username, daily_goal_minutes FROM users WHERE id = ?", (user_id,), one=True)
    streak = calculate_study_streak(user_id)
    subjects = query_db("SELECT id, name, code, target_hours_per_week FROM subjects WHERE user_id = ?", (user_id,))
    active_tasks = query_db("""
        SELECT t.id, t.title, t.priority, t.due_date, t.estimated_minutes, s.name as subject_name
        FROM tasks t
        LEFT JOIN subjects s ON t.subject_id = s.id
        WHERE t.user_id = ? AND t.status != 'completed'
        ORDER BY t.priority DESC, t.due_date ASC
    """, (user_id,))
    upcoming_exams = query_db("""
        SELECT e.title, e.exam_date, e.room_or_link, s.name as subject_name
        FROM exams e
        LEFT JOIN subjects s ON e.subject_id = s.id
        WHERE e.user_id = ? AND date(e.exam_date) >= date('now')
        ORDER BY e.exam_date ASC
        LIMIT 5
    """, (user_id,))
    stats = query_db("""
        SELECT 
            COALESCE(SUM(duration_minutes), 0) as total_mins,
            COUNT(id) as total_sessions
        FROM study_sessions
        WHERE user_id = ?
    """, (user_id,), one=True)

    today_str = date.today().strftime("%Y-%m-%d")
    today_stats = query_db("""
        SELECT COALESCE(SUM(duration_minutes), 0) as today_mins
        FROM study_sessions
        WHERE user_id = ? AND DATE(created_at) = DATE(?)
    """, (user_id, today_str), one=True)

    student_display_name = user['username'].replace('_', ' ').title() if user else "Student"

    return {
        "student_name": student_display_name,
        "streak_days": streak,
        "daily_goal_mins": user['daily_goal_minutes'] if user else 120,
        "total_study_hours": round((stats['total_mins'] or 0) / 60.0, 1) if stats else 0,
        "total_sessions": stats['total_sessions'] if stats else 0,
        "today_study_hours": round((today_stats['today_mins'] or 0) / 60.0, 1) if today_stats else 0,
        "subjects": [s['name'] for s in subjects] if subjects else [],
        "tasks": [{"title": t['title'], "priority": t['priority'], "subject": t['subject_name']} for t in active_tasks],
        "exams": [{"title": e['title'], "date": str(e['exam_date'])[:10], "subject": e['subject_name']} for e in upcoming_exams]
    }


# ---------------------------------------------------------------------------
# External LLM Providers with Multi-Turn Conversation Context
# ---------------------------------------------------------------------------
def call_gemini_api(api_key: str, system_context: str, prompt: str, chat_history: list = None):
    """Call Google Gemini API with academic system instructions and multi-turn context (ultra-fast latency)."""
    # Use verified ultra-fast Flash Lite models for sub-second responses:
    models = [
        "gemini-flash-lite-latest",
        "gemini-3.5-flash-lite"
    ]
    system_instruction = (
        "You are StudyFlow AI, an intelligent, fast academic study assistant for students. "
        "Help students learn concepts, programming, engineering, math, and exam preparation.\n"
        "Guidelines:\n"
        "1. Address the student's question directly, clearly, and concisely in simple English.\n"
        "2. When asked for an example, provide one beginner-friendly, practical code or conceptual example.\n"
        "3. Use Markdown headings (###), bullet points, and code blocks cleanly only when helpful. "
        "Do not use rigid software engineering templates unless requested.\n"
        "4. Be friendly, motivating, and focused on student learning.\n"
        f"Student Context: {system_context}"
    )

    contents = []
    if chat_history:
        # Keep last 4 turns to reduce payload token bloat and accelerate response latency
        for msg in chat_history[-4:]:
            role = "user" if msg.get("role") == "user" else "model"
            txt = msg.get("content", "").strip()
            if txt:
                contents.append({"role": role, "parts": [{"text": txt}]})
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    last_error = None
    for model in models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key.strip()}"
            payload = {
                "system_instruction": {"parts": [{"text": system_instruction}]},
                "contents": contents,
                "generationConfig": {"temperature": 0.4, "maxOutputTokens": 800}
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Connection": "keep-alive"
                }
            )
            with urllib.request.urlopen(req, timeout=6) as response:
                result = json.loads(response.read().decode("utf-8"))
                candidates = result.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
        except urllib.error.HTTPError as http_err:
            try:
                err_body = json.loads(http_err.read().decode("utf-8"))
                err_msg = err_body.get("error", {}).get("message", str(http_err))
                last_error = f"{err_msg}"
            except Exception:
                last_error = f"HTTP {http_err.code}"
            print(f"Gemini model '{model}' HTTP error: {last_error}")
            # If invalid key (400/401/403) or quota limit (429), stop looping and raise error
            if http_err.code in [400, 401, 403, 429]:
                raise ValueError(f"Google Gemini Error ({http_err.code}): {last_error}")
            continue
        except Exception as e:
            last_error = str(e)
            print(f"Gemini model '{model}' error: {e}")
            continue

    if last_error:
        raise RuntimeError(f"Google Gemini unavailable: {last_error}")
    return None

def call_openai_api(api_key: str, system_context: str, prompt: str, chat_history: list = None):
    """Call OpenAI API with full conversation context."""
    url = "https://api.openai.com/v1/chat/completions"
    messages = [
        {
            "role": "system",
            "content": (
                "You are StudyFlow AI, an expert, encouraging study assistant and mentor working like ChatGPT.\n"
                "Answer all types of student questions thoroughly: study plans, timetables, programming, coding, "
                "software projects, career guidance, and general knowledge.\n"
                "Format responses cleanly with Markdown: headings, bullet points, numbered steps, tables, and code blocks.\n\n"
                f"Student Context:\n{system_context}"
            )
        }
    ]
    if chat_history:
        for msg in chat_history[-10:]:
            role = "user" if msg.get("role") == "user" else "assistant"
            txt = msg.get("content", "").strip()
            if txt:
                messages.append({"role": role, "content": txt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.7
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )
    with urllib.request.urlopen(req, timeout=12) as response:
        result = json.loads(response.read().decode("utf-8"))
        choices = result.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "").strip()
    return None

def call_groq_api(api_key: str, system_context: str, prompt: str, chat_history: list = None):
    """Call Groq API (ultra-fast Llama 3.3) with full conversation context."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    messages = [
        {
            "role": "system",
            "content": (
                "You are StudyFlow AI, a brilliant, friendly academic mentor and tutor working like ChatGPT.\n"
                "Provide detailed, accurate answers across study techniques, timetables, programming, coding, "
                "projects, career advice, and general concepts.\n"
                "Use Markdown headings, tables, bullet points, and code blocks with syntax highlighting.\n\n"
                f"Student Profile:\n{system_context}"
            )
        }
    ]
    if chat_history:
        for msg in chat_history[-10:]:
            role = "user" if msg.get("role") == "user" else "assistant"
            txt = msg.get("content", "").strip()
            if txt:
                messages.append({"role": role, "content": txt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.6
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        result = json.loads(response.read().decode("utf-8"))
        choices = result.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "").strip()
    return None


# ---------------------------------------------------------------------------
# BUILT-IN CONVERSATIONAL CHATGPT-STYLE ENGINE
# Handles follow-ups, programming, projects, careers, timetables, and concepts
# ---------------------------------------------------------------------------

def _extract_requested_hours(q: str) -> int:
    """Extract requested study hours if mentioned in the query."""
    match = re.search(r'(\d+)\s*[-]?\s*(?:hours?|hrs?|h)\b', q)
    if match:
        val = int(match.group(1))
        if 1 <= val <= 16:
            return val
    word_map = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'twelve': 12}
    for word, num in word_map.items():
        if f"{word} hour" in q or f"{word} hr" in q or f"{word}-hour" in q:
            return num
    return 0

def _get_previous_turn_context(chat_history: list) -> str:
    """Extract the primary topic/subject from the last turn in chat history."""
    if not chat_history:
        return ""
    for msg in reversed(chat_history):
        if msg.get("role") == "user":
            return msg.get("content", "").strip()
    return ""


# --- 1. PROGRAMMING & CODING INTELLIGENCE ---
def generate_programming_response(q: str, context: dict, prev_context: str = "") -> str:
    """Generate comprehensive coding explanations, implementations, and debugging advice."""
    q_low = q.lower()
    student = context.get("student_name", "Student")

    # Palindrome query
    if "palindrome" in q_low:
        return f"""### 💻 Palindrome Check in Python (Step-by-Step)

Hello **{student}**! A **palindrome** is a string or number that reads the same backward as forward (e.g., `"radar"`, `"level"`, `"A man, a plan, a canal: Panama"`).

#### 1. Complete Python Implementation
Here is the production-grade approach handling alphanumeric characters and case-insensitivity:

```python
def is_palindrome(text: str) -> bool:
    \"\"\"
    Check if a string is a palindrome, ignoring non-alphanumeric chars and case.
    Time Complexity: O(n) | Space Complexity: O(1)
    \"\"\"
    # Left and right two-pointer approach
    left, right = 0, len(text) - 1
    
    while left < right:
        # Skip non-alphanumeric characters
        while left < right and not text[left].isalnum():
            left += 1
        while left < right and not text[right].isalnum():
            right -= 1
            
        # Compare characters in lowercase
        if text[left].lower() != text[right].lower():
            return False
            
        left += 1
        right -= 1
        
    return True

# --- Test Cases ---
if __name__ == "__main__":
    test_cases = [
        ("racecar", True),
        ("A man, a plan, a canal: Panama", True),
        ("hello world", False),
        ("Was it a car or a cat I saw?", True),
        ("12321", True)
    ]
    for string, expected in test_cases:
        result = is_palindrome(string)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print("[" + status + "] " + repr(string) + " -> " + str(result))
```

#### 2. Complexity Analysis
| Metric | Complexity | Explanation |
| :--- | :--- | :--- |
| **Time Complexity** | **$O(n)$** | We scan the string once from both ends inwards. |
| **Space Complexity** | **$O(1)$** | Two pointers in-place; no new string copies created. |

#### 3. Key Concepts to Remember
1. **Slicing Alternative**: For simple strings without punctuation, `s == s[::-1]` works in 1 line, but creates an $O(n)$ extra string copy.
2. **Two-Pointer Pattern**: Mastering the two-pointer technique is essential for LeetCode array and string interview questions!"""

    # Binary Search Tree / Trees
    if any(k in q_low for k in ["binary search tree", "bst", "binary tree"]):
        return f"""### 🌲 Binary Search Tree (BST) in Python

A **Binary Search Tree** is a hierarchical data structure where for every node:
- All values in the **left subtree** are strictly **less** than the node's value.
- All values in the **right subtree** are strictly **greater** than the node's value.

```python
class TreeNode:
    def __init__(self, val: int):
        self.val = val
        self.left = None
        self.right = None

class BinarySearchTree:
    def __init__(self):
        self.root = None

    def insert(self, val: int):
        \"\"\"Insert a value into the BST (O(log n) average).\"\"\"
        if not self.root:
            self.root = TreeNode(val)
            return
        
        curr = self.root
        while True:
            if val < curr.val:
                if not curr.left:
                    curr.left = TreeNode(val)
                    break
                curr = curr.left
            elif val > curr.val:
                if not curr.right:
                    curr.right = TreeNode(val)
                    break
                curr = curr.right
            else:
                return  # Duplicate value

    def inorder_traversal(self, node) -> list:
        \"\"\"In-order traversal yields values in sorted order!\"\"\"
        if not node:
            return []
        return self.inorder_traversal(node.left) + [node.val] + self.inorder_traversal(node.right)

# Usage
bst = BinarySearchTree()
for num in [50, 30, 70, 20, 40, 60, 80]:
    bst.insert(num)

print("Sorted BST Values:", bst.inorder_traversal(bst.root))
# Output: [20, 30, 40, 50, 60, 70, 80]
```

#### ⚡ Operations & Time Complexity
| Operation | Average Case | Worst Case (Unbalanced) |
| :--- | :--- | :--- |
| **Search** | **O(log n)** | O(n) (Skewed tree) |
| **Insertion** | **O(log n)** | O(n) |
| **In-order Traversal** | **O(n)** | O(n) |"""

    # SQL vs NoSQL
    if "sql" in q_low and "nosql" in q_low:
        return f"""### 🗄️ SQL vs. NoSQL Databases: Complete Comparison

Choosing between Relational (SQL) and Non-Relational (NoSQL) is a classic software architecture decision:

| Dimension | SQL (Relational) | NoSQL (Non-Relational) |
| :--- | :--- | :--- |
| **Data Model** | Tables with predefined schemas & foreign keys | Key-Value, Document (JSON), Columnar, Graph |
| **Schema** | **Strict / Fixed schema** (`CREATE TABLE ...`) | **Dynamic / Flexible schema** (Schemaless) |
| **Scaling** | **Vertical scaling** (Bigger CPU / RAM server) | **Horizontal scaling** (Sharding across clusters) |
| **Transactions** | Strong **ACID** properties (Banking, e-commerce) | **BASE** (Eventual consistency, high write throughput) |
| **Popular Engines**| PostgreSQL, MySQL, SQLite, Oracle | MongoDB, Redis, Cassandra, DynamoDB |

#### When to choose SQL:
- Applications with structured relationships (e.g. StudyFlow: Users ➔ Subjects ➔ Tasks ➔ Study Sessions).
- Transactions requiring financial-grade atomicity.

#### When to choose NoSQL:
- High-velocity unstructured real-time event logs, social media feeds, or gaming leaderboards."""

    # Python in simple English / beginner explanation
    if "python" in q_low:
        if any(k in q_low for k in ["simple", "example", "explain", "what is", "introduce", "beginner", "learn", "start"]):
            return f"""**Python** is a popular and beginner-friendly computer programming language. Think of it as writing instructions for a computer using plain, English-like words instead of complex, confusing symbols.

What makes Python special is that it is clean and easy to read. Unlike languages like C++ or Java that require lots of curly braces `{{}}` and semicolons `;`, Python uses simple indentation (spacing) to organize code.

It is widely used by students and professionals for:
- 🌐 **Web Development** (building web applications like StudyFlow with Flask)
- 📊 **Data Science & Statistics** (analyzing numbers and creating charts)
- 🤖 **Artificial Intelligence & Machine Learning**
- ⚡ **Automation** (writing scripts to do repetitive tasks in seconds)

---

### 💡 Beginner-Friendly Example: A Simple Study Greeting

Here is a simple Python program that greets a student and tracks their study hours:

```python
# Storing student information in simple variables
student_name = "Alex"
study_hours = 3

# Printing a friendly message to the screen
print(f"Hello, {student_name}!")
print(f"You studied for {study_hours} hours today. Keep up the great work! 🚀")
```

#### How it works:
1. **`student_name = "Alex"`** tells Python to save the text `"Alex"` in a variable.
2. **`study_hours = 3`** saves the number 3.
3. **`print(...)`** displays the message on the screen."""

    # Loops explanation
    if any(k in q_low for k in ["loop", "for loop", "while loop"]):
        return f"""### 🔄 Loops in Programming Explained

A **loop** tells the computer to repeat an action multiple times without you having to write the code over and over again.

#### Python Example:
```python
# A list of courses
subjects = ["Mathematics", "Physics", "Computer Science"]

# Loop through each course and print it
for subject in subjects:
    print(f"Reviewing notes for: {subject}")
```

- **`for` loop**: Used when you know how many times or how many items you want to go through.
- **`while` loop**: Repeats as long as a condition remains true (e.g., `while timer > 0:`)."""

    # Functions explanation
    if any(k in q_low for k in ["function", "def "]):
        return f"""### 🧩 Functions in Programming Explained

A **function** is a reusable block of code that performs one specific task. You define it once, and can run (call) it whenever you need it.

#### Python Example:
```python
# Define a function to calculate remaining study hours
def get_remaining_study_time(target_hours, hours_done):
    return target_hours - hours_done

# Call the function
remaining = get_remaining_study_time(5, 3)
print(f"You have {remaining} hours left to study today!")
```"""

    # Generic Helpful Programming Response (Direct and educational, NOT a rigid architecture template!)
    return f"""### 💻 Programming Guidance

Here is a clean, direct explanation and example to help you:

#### Key Concept
When writing programs in Python or any modern language:
- Keep your logic simple and readable.
- Break large problems into smaller, manageable steps.
- Use clear variable names that describe what they store.

#### Example Code
```python
def process_data(items):
    \"\"\"Process a list and filter out empty values.\"\"\"
    results = [item for item in items if item]
    return results

# Example usage
sample_data = ["Math", "", "Physics", "Chemistry"]
valid_subjects = process_data(sample_data)
print("Active Subjects:", valid_subjects)
```

If you have a specific error, algorithm, or course assignment you'd like to work through, please share the code and I'll explain it step-by-step!"""


# --- 2. PROJECTS & SYSTEM DESIGN ---
def generate_project_response(q: str, context: dict) -> str:
    """Generate high-yield computer science and engineering project ideas and architectures."""
    student = context.get("student_name", "Student")
    return f"""### 🚀 Top High-Impact CS Project Ideas & System Architectures

Hello **{student}**! Here are 3 industry-grade project ideas designed to stand out in resumes and technical interviews:

---

#### 1. 🤖 AI-Powered Smart Study & Spaced Repetition Platform (Full-Stack)
- **Problem**: Students suffer from information overload and forget 80% of what they learn without spaced intervals.
- **Tech Stack**:
  - **Frontend**: React / Next.js or Vanilla HTML5 + CSS Glassmorphism
  - **Backend**: Python (FastAPI / Flask) + SQLite / PostgreSQL
  - **AI / ML**: OpenAI / Gemini API for automatic flashcard generation from PDF notes + Ebbinghaus forgetting curve algorithms.
- **Key Feature**: Focus room with automated background sound synthesis and Pomodoro analytics.

---

#### 2. ⚡ Real-Time Collaborative Code Editor & Pair Programming Room
- **Problem**: Remote developers and students need zero-latency synchronous code sharing with syntax highlighting.
- **Tech Stack**:
  - **Frontend**: Monaco Editor (VS Code engine) + Tailwind CSS
  - **Backend**: Node.js + Socket.io / WebSockets + Redis for live cursor synchronization
  - **Execution Sandbox**: Docker containers for secure sandboxed Python/JS code execution.
- **Key Feature**: Live voice/chat room and instant shareable workspace URLs.

---

#### 3. 🛡️ Decentralized Resume & Credential Verification Portal
- **Problem**: Fake credentials and diploma fraud in corporate hiring.
- **Tech Stack**:
  - **Frontend**: React + Ethers.js
  - **Backend**: Node.js or Python Flask
  - **Database**: IPFS (InterPlanetary File System) + Ethereum / Polygon Testnet smart contracts.
- **Key Feature**: Universities issue cryptographically signed soulbound tokens; recruiters verify authenticity in 1 click without third-party brokers.

---

#### 📋 Recommended 4-Step Project Delivery Plan:
1. **Week 1 (Schema & Wireframes)**: Design ER diagrams, REST API endpoints, and Figma mockups.
2. **Week 2 (Core Backend & DB)**: Build models, authentication, and CRUD endpoints with tests.
3. **Week 3 (Frontend Integration)**: Connect UI components, handle loading spinners and error toasts.
4. **Week 4 (Deployment & README)**: Deploy on Render/Vercel, record a 2-minute demo video, and write an elite GitHub README."""


# --- 3. CAREER GUIDANCE & INTERVIEW PREPARATION ---
def generate_career_response(q: str, context: dict) -> str:
    """Generate career path guidance, tech interview strategies, and resume advice."""
    student = context.get("student_name", "Student")
    return f"""### 🎯 Software Engineering Career & Interview Blueprint for {student}

Cracking top software engineering roles requires mastering technical problem solving, system design, and behavioral storytelling:

---

#### 1. The 4-Phase Tech Interview Preparation Roadmap

| Phase | Timeline | Core Focus | Daily Target |
| :--- | :--- | :--- | :--- |
| **Phase 1: DSA Foundations** | Months 1–2 | Arrays, Hash Maps, Two Pointers, Trees, Graphs, DP | 2 LeetCode Mediums daily (Pattern-based) |
| **Phase 2: System Design** | Month 3 | Caching, Load Balancers, Sharding, Microservices | Study 1 architecture/week (e.g., URL Shortener) |
| **Phase 3: Portfolio & Resume** | Month 4 | 2 production-grade deployed projects on GitHub | Polish GitHub READMEs with live demo links |
| **Phase 4: Mock Interviews** | Month 5 | Timed problem solving on Pramp / interviewing.io | Practice thinking out loud under 45m timer |

---

#### 2. The STAR Method for Behavioral Interviews
Top tech companies (FAANG, Fortune 500) evaluate communication through behavioral questions (*"Tell me about a time you solved a tough conflict or deadline"*):
- **S (Situation)**: Set the scene (e.g. *"In my 3rd year database project, we had 48 hours before the deadline..."*)
- **T (Task)**: State your objective (*"Our database queries were taking 8 seconds under load."*)
- **A (Action)**: What **YOU** specifically did (*"I profiled queries, added composite B-Tree indexes, and cached read queries using Redis."*)
- **R (Result)**: Quantifiable outcome (*"Query latency dropped by 92% to 600ms, and we earned an 'A' grade."*)

---

#### 3. Top 3 Resume Traps to Avoid
1. **Don't list tutorial clones**: Avoid generic todo-apps or calculator apps; build projects that solve real problems with authentication and persistence.
2. **Quantify achievements**: Use the Google formula: *"Accomplished [X], as measured by [Y], by doing [Z]"*.
3. **Clean single-page format**: Keep your resume strictly to 1 page with clean ATS-friendly typography."""


# --- 4. FOLLOW-UP QUESTIONS & CONTEXT AWARENESS ---
def generate_followup_response(q: str, context: dict, prev_turn: str) -> str:
    """Intelligently respond to follow-up questions referencing previous messages."""
    student = context.get("student_name", "Student")
    q_low = q.lower()

    if any(k in q_low for k in ["code", "python", "implementation", "write it"]):
        return f"""### 💻 Follow-Up Implementation & Code Snippet

Building directly on our previous discussion about **"{prev_turn[:40]}..."**:

Here is the complete, working code implementation with comments and edge case handling:

```python
# Follow-up implementation
def execute_solution():
    \"\"\"
    Structured, production-ready solution with clean logic.
    \"\"\"
    print("Executing solution based on your previous request...")
    # Add your specific data inputs
    data = [1, 2, 3, 4, 5]
    result = [x * 2 for x in data]
    return result

if __name__ == "__main__":
    output = execute_solution()
    print("Result:", output)
```

#### 🔍 Step-by-Step Breakdown:
1. **Data Ingestion**: Clean inputs and reject invalid parameters upfront.
2. **Execution**: Perform the core transformation in $O(n)$ linear time.
3. **Verification**: Run assertions to verify expected output matches actual output.

Let me know if you would like me to adapt this to a specific language (JavaScript, C++, Java, or SQL)!"""

    if any(k in q_low for k in ["simplify", "explain more", "easier", "simple terms", "eli5"]):
        return f"""### 💡 Simplified Explanation (In Plain English)

Let's break down **"{prev_turn[:40]}..."** into the simplest possible everyday terms, **{student}**:

#### 🧠 The Core Idea in 1 Sentence:
Think of this concept like an everyday kitchen recipe: you have your **ingredients** (inputs), the **cooking process** (the rules or algorithm), and the **finished meal** (the output).

#### 🌟 3 Simple Steps to Master It:
1. **The 'Why'**: We use this technique to save time and avoid repeating tedious work.
2. **The 'How'**: Break down the big challenge into 2–3 bite-sized steps that take less than 10 minutes each.
3. **The 'Test'**: If you can explain it to a 10-year-old without using technical buzzwords, you have 100% understood it!

Would you like a concrete real-world example, a diagram, or a practice exercise?"""

    return f"""### 💡 Context-Aware Follow-Up for {student}

Continuing from our discussion regarding **"{prev_turn[:50]}..."**:

Here are the key next steps and deeper insights:
1. **Immediate Action Item**: Put the discussed concept into practice today using a focused 25m Pomodoro block.
2. **Deepening Knowledge**: Review related edge cases and practice 2–3 active recall self-quiz questions.
3. **Next Direction**: Would you like code examples, a study timetable for this, or a practice question?"""


# --- 5. TIMETABLES & DAILY ROUTINES ---
def generate_timetable_response(q: str, context: dict) -> str:
    """Generate all variations of study timetables and daily routines."""
    student = context.get("student_name", "Student")
    hours = _extract_requested_hours(q)
    is_night_owl = any(k in q for k in ["night", "late night", "owl", "midnight", "evening only", "night study"])
    is_morning = any(k in q for k in ["morning", "5 am", "early bird", "sunrise", "6 am"])
    is_school = any(k in q for k in ["school", "class 10", "class 12", "high school", "cbse", "icse", "school student"])
    is_college = any(k in q for k in ["college", "university", "engineering student", "campus", "undergrad", "btech", "degree"])
    is_working = any(k in q for k in ["working", "job", "office", "work and study", "part time", "full time job", "professional"])
    is_weekend = any(k in q for k in ["weekend", "saturday", "sunday", "sat & sun"])
    is_weekly = any(k in q for k in ["weekly", "7 day", "7 days", "mon to sun", "whole week", "monday to friday"])

    # 1. Weekly (7-Day) Master Timetable
    if is_weekly:
        subjs = context.get("subjects") or ["Subject A (Analytical)", "Subject B (Conceptual)", "Subject C (Problem-Solving)"]
        s1 = subjs[0] if len(subjs) > 0 else "Math / Coding"
        s2 = subjs[1] if len(subjs) > 1 else "Physics / Core Science"
        s3 = subjs[2] if len(subjs) > 2 else "Theory / Humanities"
        return f"""### 📅 Master 7-Day Weekly Study Timetable

A structured weekly system prevents burnout, interleaves subjects, and guarantees retention for **{student}**:

| Day | Primary Subject (Morning) | Secondary Subject (Afternoon) | Evening Focus & Review | Weekly Goal |
| :--- | :--- | :--- | :--- | :--- |
| **Monday** | 📐 **{s1}** (Concept Deep-dive) | 🔬 **{s2}** (Formula Derivations) | Active Recall & Flashcards | Kickstart momentum |
| **Tuesday** | 📚 **{s3}** (Core Reading) | 📐 **{s1}** (Problem Sets) | Homework & Assignment Sprint | Analytical practice |
| **Wednesday** | 🔬 **{s2}** (Problem Solving) | 📚 **{s3}** (Mind Mapping) | Flashcard Review & Weak Areas | Midway checkpoint |
| **Thursday** | 📐 **{s1}** (Advanced Numericals)| 🔬 **{s2}** (Case Studies/Labs) | Blurting Method Practice | Reinforce tricky topics |
| **Friday** | 📚 **{s3}** (Summary Notes) | 📐 **{s1}** (Speed Drills) | Week-End Task Clearance | Clear pending tasks |
| **Saturday** | 🏆 **Full Mock Test Simulation**| 🔍 **Detailed Error Analysis** | Deep Dive on Missed Questions| Exam readiness |
| **Sunday** | 🔄 **Weekly Comprehensive Review**| 📋 **StudyFlow Planning for Next Week**| 🌴 Half-Day Rest & Hobbies | Mental restoration |

#### 🔑 Weekly Principles:
1. **Never skip Saturday Error Analysis**: Reviewing *why* you got a mock question wrong is where 80% of grade gains happen.
2. **Protect Sunday Afternoon**: Rest is productive. A rested student learns twice as fast on Monday."""

    # 2. Weekend Timetable
    if is_weekend:
        return f"""### ⚡ High-Yield Weekend Study Timetable (Sat & Sun)

Weekends are your secret weapon to surpass your academic targets. Here is a marathon weekend plan:

| Weekend Slot | Saturday Focus (Deep Work & Testing) | Sunday Focus (Review & Reset) |
| :--- | :--- | :--- |
| **08:00 AM – 09:00 AM** | Healthy breakfast & daily setup | Morning walk, coffee, plan targets |
| **09:00 AM – 12:00 PM** | 🎯 **3-Hour Timed Mock Test Simulation** | 🔍 **Deep Error Log & Correction of Mock** |
| **12:00 PM – 01:30 PM** | Nutritious lunch & 20-min power nap | Lunch & relaxing with family/friends |
| **01:30 PM – 04:00 PM** | 📚 **Backlog Clearance (Toughest Subject)** | 🧠 **Active Recall & Flashcard Marathon** |
| **04:00 PM – 05:30 PM** | Outdoor workout or walk (Offline) | Creative hobby or leisure time |
| **05:30 PM – 07:30 PM** | 💻 **Assignment & Project Completion** | 📅 **Plan Week Ahead in StudyFlow** |
| **07:30 PM – 09:00 PM** | Dinner & movie / relaxation | Relaxing dinner, light reading |
| **09:00 PM – 10:00 PM** | Light recap of day's formulas | Early sleep prep for Monday morning |

**Weekend Gain**: **12+ Focused Hours** without feeling exhausted!"""

    # 3. Explicit Hours Request
    if hours > 0:
        if hours <= 4:
            return f"""### ⏱️ Focused {hours}-Hour Daily Study Timetable

Designed for maximum retention in limited time for **{student}**:

| Time Slot | Duration | Activity | Purpose |
| :--- | :--- | :--- | :--- |
| **06:00 AM – 07:30 AM** | 90 Mins | 🎯 **Core Concept Block (Hardest Subject)** | Peak willpower before daily fatigue |
| **05:30 PM – 07:00 PM** | 90 Mins | 📝 **Active Problem Solving & Exercises** | High-energy retrieval practice |
| **09:30 PM – 10:30 PM** | 60 Mins | 🔄 **Spaced Repetition & Flashcard Drill** | Consolidate memories before sleep |

**Key Strategy**: With a {hours}-hour budget, strictly avoid passive reading. Spend 70% of time solving problems and self-quizzing."""

        elif hours == 8:
            return f"""### 📅 Dedicated 8-Hour Daily Study Timetable (4 × 2-Hour Blocks)

Designed for peak cognitive retention across 4 distinct deep work sessions for **{student}**:

| Time Slot | Phase & Block | Core Activity | Strategy |
| :--- | :--- | :--- | :--- |
| **06:30 AM – 07:15 AM** | 🌅 Morning Setup | Hydration, sunlight exposure, nutritious breakfast | High alertness |
| **07:15 AM – 09:15 AM** | 🎯 **Block 1 (2 Hours)** | **Primary Hard Course**: High-difficulty theory & proofs | Peak willpower |
| **09:15 AM – 09:45 AM** | ☕ Active Rest | Physical stretch, healthy snack, hydration | Screen-free |
| **09:45 AM – 11:45 AM** | 📝 **Block 2 (2 Hours)** | **Analytical Practice**: Problem sets & question banks | Active recall |
| **11:45 AM – 01:30 PM** | 🥗 Lunch & Recharge | Wholesome meal, 20-min power rest | Full recovery |
| **01:30 PM – 03:30 PM** | 🔬 **Block 3 (2 Hours)** | **Secondary Subject**: Notes synthesis, diagrams, case studies | Interleaving |
| **03:30 PM – 05:30 PM** | 🏃 Exercise / Free Time | Gym, walk, outdoor hobbies, family/friends | Dopamine reset |
| **05:30 PM – 07:30 PM** | 🔄 **Block 4 (2 Hours)** | **Past Papers & Spaced Review**: Drill flashcards, error log | Consolidation |
| **07:30 PM – 08:30 PM** | 🍲 Dinner & Relaxation | Relaxed dinner, light reading | Leisure |
| **08:30 PM – 09:30 PM** | 📋 Day Wrap-up & StudyFlow Log | Log completed blocks, protect your **{context.get('streak_days', 0)}-day streak** | Closure |
| **10:30 PM – 06:30 AM** | 😴 Quality Sleep (8 Hours) | Solidify learned concepts into long-term memory | Recovery |

#### ⚡ 3 Rules to Execute This 8-Hour Timetable:
1. **The 20-Second Rule**: Prepare your desk the night before so zero friction delays Block 1.
2. **Never Study on Your Bed**: Keep the study zone strictly separate from relaxation zones.
3. **Use the Focus Room**: Track each 2-hour session in StudyFlow with the 50/10 Pomodoro mode."""

        elif hours >= 10:
            return f"""### 🏆 Intensive {hours}-Hour Marathon Timetable (Exam Sprint Mode)

For high-stakes entrance exams and competitive test preparation:

| Time Slot | Duration | Focus Area | Protocol |
| :--- | :--- | :--- | :--- |
| **06:00 AM – 08:30 AM** | 2.5 Hours | ⚡ **Session 1: High-Yield Numericals / Math** | Pomodoro 50/10 x 2 |
| **08:30 AM – 09:15 AM** | 45 Mins | 🍳 Breakfast & Fresh Air | Screen-free recharge |
| **09:15 AM – 12:15 PM** | 3.0 Hours | 🔬 **Session 2: Deep Core Theory & Derivations** | Pomodoro 50/10 x 3 |
| **12:15 PM – 01:45 PM** | 90 Mins | 🥗 Lunch & 20-min restorative nap | Nap resets adenosine |
| **01:45 PM – 04:45 PM** | 3.0 Hours | 📝 **Session 3: Timed Question Bank / Past Papers**| Simulate exam conditions |
| **04:45 PM – 06:00 PM** | 75 Mins | 🏃 Cardio Walk / Refreshment / Snack | Physical recharge |
| **06:00 PM – 08:00 PM** | 2.0 Hours | 📖 **Session 4: Second Subject Rotation / Review**| Cross-subject interleaving |
| **08:00 PM – 09:00 PM** | 60 Mins | 🍲 Dinner & Family Time | Mental breather |
| **09:00 PM – 10:30 PM** | 1.5 Hours | 🔍 **Session 5: Error Log & Flashcard Recall** | Close knowledge gaps |
| **10:30 PM – 06:00 AM** | 7.5 Hours | 😴 Deep Restorative Sleep | Essential for retention |

**Total Pure Study**: **{hours} Hours** structured to prevent burnout with 4 restorative breaks!"""

        else:
            return f"""### 📅 Balanced {hours}-Hour Daily Study Timetable

Here is a scientifically optimized {hours}-hour daily schedule tailored for **{student}**:

| Time Slot | Block Type | Focus & Tasks | Strategy |
| :--- | :--- | :--- | :--- |
| **06:30 AM – 07:15 AM** | Morning Routine | Hydration, sunlight exposure, healthy breakfast | Alertness |
| **07:15 AM – 09:15 AM** | 🎯 **Block 1 (2 Hours)** | **Primary Difficult Course**: Core theory & proofs | Deep Work |
| **09:15 AM – 09:45 AM** | ☕ Active Break | Stretching, fruit / nuts, hydration | No social media |
| **09:45 AM – 11:45 AM** | 📝 **Block 2 (2 Hours)** | **Problem Solving**: Practice sets & question bank | Active Recall |
| **11:45 AM – 01:30 PM** | 🥗 Lunch & Recharge | Wholesome meal, 20-min power rest | Rest |
| **01:30 PM – 03:30 PM** | 🔬 **Block 3 (2 Hours)** | **Secondary Subject**: Readings & notes synthesis | Interleaving |
| **03:30 PM – 05:30 PM** | 🏃 Exercise / Free Time | Gym, walk, hobbies, socializing | Reset dopamine |
| **05:30 PM – 07:00 PM** | 🔄 **Block 4 ({max(hours-6, 1)} Hour)** | **Revision & Flashcards**: Spaced repetition drills | Consolidation |
| **07:30 PM – 08:30 PM** | 🍲 Dinner & Family Time | Relaxed evening meal | Leisure |
| **08:30 PM – 09:30 PM** | 📋 Day Closure & StudyFlow Log| Log completed tasks, check study streak | Habit loop |
| **10:30 PM – 06:30 AM** | 😴 Deep Sleep (8 Hours) | Solidify learned concepts into long-term memory | Recovery |"""

    # 4. School Student Routine
    if is_school:
        return f"""### 🎒 Optimized Daily Timetable for School Students

Hello **{student}**! Balancing school hours, homework, and self-study:

| Time Slot | Phase & Activity | Focus / Output Objective | Energy Level |
| :--- | :--- | :--- | :--- |
| **06:00 AM – 06:45 AM** | 🌅 Morning Freshen Up & Breakfast | Hydration, healthy breakfast, bag check | Medium |
| **06:45 AM – 07:30 AM** | ⚡ Quick Formula / Vocabulary Review | 45m light revision before classes | High |
| **07:30 AM – 02:30 PM** | 🏫 School Classes & Active Listening | Take Cornell notes, engage in lectures | Steady |
| **02:30 PM – 03:45 PM** | 🥗 Lunch, Relaxation & Decompression | Shower, meal, nap / physical activity | Low (Rest) |
| **03:45 PM – 05:15 PM** | 📚 **Study Block 1: School Homework & Math** | Complete assigned homework & numericals | High |
| **05:15 PM – 05:45 PM** | 🚶 Outdoor Break / Snack / Sports | Disconnect from screens, light exercise | Recharge |
| **05:45 PM – 07:15 PM** | 🔬 **Study Block 2: Science / Heavy Subject** | Deep concept understanding & active recall | Peak Focus |
| **07:15 PM – 07:30 PM** | ☕ Refreshment Break | Hydrate, quick stretch | Recharge |
| **07:30 PM – 08:45 PM** | 📖 **Study Block 3: Languages / Social Studies** | Reading, writing answers & summaries | Medium |
| **08:45 PM – 09:30 PM** | 🍲 Dinner & Family Time | Relaxed dinner, no study talk | Low |
| **09:30 PM – 10:15 PM** | 📝 Daily Recap & Tomorrow's Bag Packing | 15m flashcards, plan next day in StudyFlow | Light |
| **10:15 PM – 06:00 AM** | 😴 Quality Sleep (7.75 Hours) | Memory consolidation & recovery | Deep Rest |"""

    # 5. College Student Routine
    if is_college:
        return f"""### 🎓 Strategic Daily Timetable for College & University Students

Hello **{student}**! Balancing lectures, coding, projects, and self-study:

| Time Slot | Segment | Core Action | Recommended Focus |
| :--- | :--- | :--- | :--- |
| **07:00 AM – 08:00 AM** | Morning Awakening | Hydration, healthy breakfast, plan day | Clean start |
| **08:00 AM – 09:00 AM** | ⚡ Pre-Class Power Hour | Review lecture slides before attending | 100% Comprehension |
| **09:00 AM – 01:00 PM** | 🏛️ College Lectures / Labs | Active note-taking, lab assignments | College hours |
| **01:00 PM – 02:00 PM** | 🥗 Lunch & Social Break | Campus lunch, mental breather | Rest |
| **02:00 PM – 04:00 PM** | 🏛️ Afternoon Lectures / Library Block | Use gap hours for library reading | Steady focus |
| **04:30 PM – 05:30 PM** | ☕ Campus Travel & Unwind | Coffee, gym / walk, digital downtime | Transition |
| **05:30 PM – 07:30 PM** | 💻 **Deep Study Block 1 (Hardest Course)** | Coding / Problem Sets / Core Theory | Deep Work |
| **07:30 PM – 08:00 PM** | 🧘 Mindful Break | Dinner prep, listening to music | Reset |
| **08:00 PM – 09:30 PM** | 📝 **Deep Study Block 2 (Project / Assignments)**| Lab reports, term papers, weekly quiz prep | Output driven |
| **09:30 PM – 10:15 PM** | 🍲 Dinner & Leisure | Dinner, chat with friends | Unwind |
| **10:15 PM – 11:15 PM** | 🔄 Spaced Repetition & Day Wrap-up | Flashcards, update StudyFlow streak | Review |
| **11:15 PM – 07:00 AM** | 😴 Sleep (7.75 Hours) | Essential for neuroplasticity & retention | Full rest |"""

    # 6. Night Owl Routine
    if is_night_owl:
        return f"""### 🦉 High-Performance Night Owl Study Timetable

For students who reach peak cognitive clarity late in the evening:

| Time Slot | Phase | Focus & Tasks | State |
| :--- | :--- | :--- | :--- |
| **10:00 AM – 10:45 AM** | ☀️ Morning Rise & Sunlight | Wake up, natural light exposure, water | Circadian reset |
| **10:45 AM – 12:00 PM** | 🍳 Brunch & Light Planning | Plan day in StudyFlow, organize study desk | Steady start |
| **12:00 PM – 02:00 PM** | 📚 **Afternoon Study Session 1 (2h)** | Conceptual reading, summaries, lectures | Medium focus |
| **02:00 PM – 03:00 PM** | 🍲 Lunch & Walk | Wholesome meal, physical movement | Refresh |
| **03:00 PM – 05:30 PM** | 📝 **Afternoon Study Session 2 (2.5h)**| Assignments, homework, lab work | Active output |
| **05:30 PM – 07:00 PM** | 🏃 Exercise & Social Time | Workout, errands, social connection | High energy |
| **07:00 PM – 08:00 PM** | 🥗 Dinner & Transition | Light dinner, prepare nocturnal workspace | Prepare |
| **08:00 PM – 10:30 PM** | ⚡ **Prime Night Block 1 (2.5h)** | **Hardest Subject**: Complex problem-solving | Peak Concentration |
| **10:30 PM – 11:00 PM** | 🍵 Herbal Tea & Stretch Break | No bright overhead lights, quiet rest | Maintenance |
| **11:00 PM – 01:30 AM** | 🔬 **Prime Night Block 2 (2.5h)** | Past papers, timed mock tests, deep code | Deep Quiet Flow |
| **01:30 AM – 02:00 AM** | 🌙 Wind-down & Blue Light Cut | Journaling, room dark, prep for sleep | Sleep prep |
| **02:00 AM – 10:00 AM** | 😴 Deep Rest (8 Full Hours) | Pitch-black room for restorative sleep | Recovery |"""

    # Default Balanced Timetable (6 Hours)
    return f"""### 📅 Balanced 6-Hour Daily Study Timetable

Here is a scientifically optimized 6-hour daily schedule tailored for **{student}**:

| Time Slot | Block Type | Focus & Tasks | Strategy |
| :--- | :--- | :--- | :--- |
| **06:30 AM – 07:15 AM** | Morning Routine | Hydration, sunlight exposure, healthy breakfast | Alertness |
| **07:15 AM – 09:15 AM** | 🎯 **Block 1 (2 Hours)** | **Primary Difficult Course**: Core theory & proofs | Deep Work |
| **09:15 AM – 09:45 AM** | ☕ Active Break | Stretching, fruit / nuts, hydration | No social media |
| **09:45 AM – 11:45 AM** | 📝 **Block 2 (2 Hours)** | **Problem Solving**: Practice sets & question bank | Active Recall |
| **11:45 AM – 01:30 PM** | 🥗 Lunch & Recharge | Wholesome meal, 20-min power rest | Rest |
| **01:30 PM – 03:30 PM** | 🔬 **Block 3 (2 Hours)** | **Secondary Subject**: Readings & notes synthesis | Interleaving |
| **03:30 PM – 05:30 PM** | 🏃 Exercise / Free Time | Gym, walk, hobbies, socializing | Reset dopamine |
| **05:30 PM – 06:30 PM** | 🔄 **Review Block (1 Hour)** | **Revision & Flashcards**: Spaced repetition drills | Consolidation |
| **07:30 PM – 08:30 PM** | 🍲 Dinner & Family Time | Relaxed evening meal | Leisure |
| **08:30 PM – 09:30 PM** | 📋 Day Closure & StudyFlow Log| Log completed tasks, check study streak | Habit loop |
| **10:30 PM – 06:30 AM** | 😴 Deep Sleep (8 Hours) | Solidify learned concepts in long-term memory | Recovery |"""


# --- 6. STUDY PLANS (ANY SUBJECT) ---
def generate_study_plan_response(q: str, context: dict) -> str:
    """Generate high-yield, structured 4-phase study plans for any subject."""
    student = context.get("student_name", "Student")
    enrolled = context.get("subjects", [])
    
    # Subject detection
    subject_name = "Core Subject"
    for s in enrolled:
        if s.lower() in q.lower():
            subject_name = s
            break
    if subject_name == "Core Subject":
        m = re.search(r'(?:study plan|roadmap|plan for|guide for|how to study|how to prepare for|learn)\s+(?:for\s+|in\s+|about\s+)?([a-zA-Z0-9\+\#\s]{2,35}?)(?:\?|\.|$|\s+in\s+|\s+for\s+)', q, flags=re.IGNORECASE)
        if m:
            subject_name = re.sub(r'^(my|the|an|a|exam|test|for|in|about)\s+', '', m.group(1).strip(), flags=re.IGNORECASE).title()
        else:
            subject_name = "Computer Science & Engineering"

    timeframe = "4-Week Mastery"
    if any(k in q.lower() for k in ["30 day", "30-day", "month"]):
        timeframe = "30-Day Comprehensive"
    elif any(k in q.lower() for k in ["7 day", "7-day", "1 week"]):
        timeframe = "7-Day Sprint"

    return f"""### 🎯 {timeframe} Study Plan: **{subject_name}**

Hello **{student}**! Here is an elite, structured academic roadmap tailored specifically for **{subject_name}**:

#### 🗺️ 4-Phase Mastery Blueprint

| Phase | Timeline | Core Focus & Milestones | Actionable Deliverable |
| :--- | :--- | :--- | :--- |
| **Phase 1: Foundations** | Days 1 – 7 | Master core syntax, foundational theory, definitions | 1-page Concept Map of all core topics |
| **Phase 2: Deep Application** | Days 8 – 18 | Hands-on exercises, coding problems, derivations | 50+ Solved Practice Questions / Mini-Labs |
| **Phase 3: Retrieval & Synthesis** | Days 19 – 25 | Active recall flashcards, timed quizzes, cheat sheet | Master Formula & Summary Cheat Sheet |
| **Phase 4: Exam Simulation** | Days 26 – 30 | Past papers, mock tests under strict exam conditions | 2–3 Full Past Papers graded strictly |

---

#### ⏱️ Recommended Daily Study Routine for {subject_name}
- **Block 1 (45 Mins)**: Active Recall from yesterday's session (Closed-book self-test).
- **Block 2 (60 Mins)**: New topic ingestion (Read 1 chapter / watch 1 lecture with Cornell notes).
- **Block 3 (60 Mins)**: Problem solving & application (Drill questions, coding, or derivations).
- **Block 4 (15 Mins)**: 15-minute quick recap and log progress into StudyFlow."""


# --- 7. GENERAL KNOWLEDGE & CONCEPT EXPLAINER ---
def generate_concept_explanation(q: str, context: dict) -> str:
    """Generate pedagogical explanation for general concepts and student doubts."""
    student = context.get("student_name", "Student")
    clean_topic = re.sub(r'^(what is|explain|define|how does|what are|tell me about|how to understand|difference between)\s+', '', q, flags=re.IGNORECASE).strip().rstrip('?')
    if not clean_topic:
        clean_topic = "Your Academic Topic"

    return f"""### 💡 Deep Dive & Conceptual Breakdown: **{clean_topic.title()}**

Hello **{student}**! Here is an intuitive, comprehensive explanation of **{clean_topic}**:

#### 📌 1. Plain-English Intuition & Definition
At its core, **{clean_topic.title()}** is a fundamental principle that governs how systems, algorithms, or natural forces operate. Instead of rote memorization, understand it as an **input ➔ transformation ➔ output** mechanism.

#### 🧠 2. Real-World Mental Model (Analogy)
Think of this concept like an everyday system:
- **The Input**: The initial components or data supplied.
- **The Engine / Rule**: The underlying transformation logic that dictates how entities interact.
- **The Result**: The stable, predictable outcome achieved once the process concludes.

#### ⚙️ 3. Key Principles & Mechanics
1. **Core Mechanism**: Focus on *why* this principle occurs, not just the surface definition.
2. **Boundary Conditions**: Understand the edge cases where this concept changes or no longer applies.
3. **Practical Application**: In real-world projects and exams, recognize the key trigger words that indicate this concept is tested.

#### ❓ 4. Self-Test Question (Active Recall):
> *Can you explain the main mechanism of {clean_topic} out loud right now in 60 seconds without checking your notes?*

Feel free to ask for sample code, numerical examples, or a practice quiz on this!"""


# ---------------------------------------------------------------------------
# MAIN AI ENTRYPOINT
# ---------------------------------------------------------------------------
def ask_study_ai(user_id: int, prompt: str, chat_history: list = None) -> str:
    """Main entrypoint for student AI queries.
    Seamlessly uses configured LLM (Gemini, Groq, OpenAI), or falls back
    to the rich built-in conversational ChatGPT engine.
    """
    if not prompt or not prompt.strip():
        return "Please ask a question, request a timetable, or ask for coding/study guidance!"

    context = get_student_study_context(user_id)
    task_titles = [t['title'] for t in context.get('tasks', [])[:4]]
    tasks_summary = ', '.join(task_titles) if task_titles else 'None'
    exam_titles = [f"{e['title']} ({e['date']})" for e in context.get('exams', [])[:3]]
    exams_summary = ', '.join(exam_titles) if exam_titles else 'None'
    courses_summary = ', '.join(context.get('subjects', [])) or 'General Studies'
    system_context = (
        f"Student: {context['student_name']}, Streak: {context['streak_days']} days, "
        f"Courses: {courses_summary}, Tasks: {tasks_summary}, Exams: {exams_summary}"
    )

    active_provider = os.environ.get("AI_ACTIVE_PROVIDER", "").lower().strip()

    # 1. Google Gemini (if preferred or key present)
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if gemini_key and (active_provider == "gemini" or not active_provider):
        try:
            res = call_gemini_api(gemini_key, system_context, prompt, chat_history)
            if res:
                return res
        except (ValueError, RuntimeError) as e:
            if active_provider == "gemini":
                return f"⚠️ **Google Gemini Notice:** {str(e)}\n\nPlease verify your API key in **⚙️ Config** or switch to the Built-in Assistant."
            print(f"Gemini API error: {e}")
        except Exception as e:
            if active_provider == "gemini":
                return f"⚠️ **Google Gemini Notice:** Failed to connect ({str(e)}). Please check your connection or API key."
            print(f"Gemini API error: {e}")

    # 2. Groq (if preferred or key present)
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    if groq_key and (active_provider == "groq" or not active_provider):
        try:
            res = call_groq_api(groq_key, system_context, prompt, chat_history)
            if res:
                return res
        except Exception as e:
            if active_provider == "groq":
                return f"⚠️ **Groq API Notice:** {str(e)}\n\nPlease verify your API key in **⚙️ Config**."
            print(f"Groq API fallback: {e}")

    # 3. OpenAI (if preferred or key present)
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if openai_key and (active_provider == "openai" or not active_provider):
        try:
            res = call_openai_api(openai_key, system_context, prompt, chat_history)
            if res:
                return res
        except Exception as e:
            if active_provider == "openai":
                return f"⚠️ **OpenAI API Notice:** {str(e)}\n\nPlease verify your API key in **⚙️ Config**."
            print(f"OpenAI API fallback: {e}")

    # 4. Fallback checks for any remaining configured keys
    for candidate_key, caller in [(groq_key, call_groq_api), (gemini_key, call_gemini_api), (openai_key, call_openai_api)]:
        if candidate_key:
            try:
                res = caller(candidate_key, system_context, prompt, chat_history)
                if res:
                    return res
            except Exception:
                pass

    # -----------------------------------------------------------------------
    # 5. BUILT-IN CONVERSATIONAL CHATGPT-STYLE ENGINE
    # -----------------------------------------------------------------------
    q = prompt.lower().strip()
    prev_turn = _get_previous_turn_context(chat_history)

    # Check for Follow-Up question
    is_followup = any(w in q for w in ["for that", "for this", "the code", "step 2", "simplify", "explain more", "what about", "how about that", "give me code", "write it"]) and len(prev_turn) > 0
    if is_followup:
        return generate_followup_response(prompt, context, prev_turn)

    # Programming & Coding
    coding_keywords = ["python", "javascript", "java", "c++", "coding", "code", "function", "algorithm", "dsa", "sql", "bug", "debug", "binary tree", "palindrome", "loop", "array", "database", "api", "react", "html", "css"]
    if any(k in q for k in coding_keywords):
        return generate_programming_response(prompt, context, prev_turn)

    # Projects & System Design
    project_keywords = ["project idea", "project", "portfolio", "system design", "architecture", "final year", "mini project", "build an app"]
    if any(k in q for k in project_keywords):
        return generate_project_response(prompt, context)

    # Career & Interview Guidance
    career_keywords = ["career", "interview", "resume", "cv", "job", "internship", "star method", "hire", "salary", "faang", "software engineer", "developer roadmap"]
    if any(k in q for k in career_keywords):
        return generate_career_response(prompt, context)

    # Timetables & Schedules
    timetable_keywords = ["timetable", "time-table", "time table", "schedule", "routine", "daily schedule", "study hours", "night owl", "morning routine", "weekend", "school routine", "college schedule", "working student", "weekly routine"]
    if any(k in q for k in timetable_keywords):
        return generate_timetable_response(prompt, context)

    # Study Plans & Syllabi
    study_plan_keywords = ["study plan", "roadmap", "how to prepare", "how to study", "syllabus", "30 day plan", "revision plan", "guide for"]
    if any(k in q for k in study_plan_keywords):
        return generate_study_plan_response(prompt, context)

    # What should I study today / Database Context
    if any(k in q for k in ["what should i study", "today", "priorit", "my tasks", "my exams"]):
        tasks = context.get("tasks", [])
        exams = context.get("exams", [])
        task_str = "\n".join([f"- 📌 **{t['title']}** (Priority: `{t['priority'].upper()}` | Subject: *{t.get('subject') or 'General'}*)" for t in tasks[:4]]) if tasks else "- No pending tasks! Time for a 25m focus sprint."
        nearest_exam = f"⚠️ Upcoming Milestone: **{exams[0]['title']}** on `{exams[0]['date']}`!" if exams else "Keep consistent momentum!"
        return f"""### 🎯 Personalized Priority Roadmap for {context['student_name']}

Based on your active study profile (**{context['streak_days']}-day streak**, **{context['total_study_hours']}h total studied**):

#### 📋 High-Impact Tasks:
{task_str}

#### 📅 Exam Status:
{nearest_exam}

#### ⚡ Tactical Recommendation:
1. Launch a **25-minute Pomodoro** session in the **Focus Room** on your top task.
2. Maintain your momentum to keep your **{context['streak_days']}-day streak** growing!"""

    # General Knowledge & Concept Explanations
    explanation_keywords = ["what is", "explain", "how does", "what are", "difference between", "why do", "define", "meaning of", "how to"]
    if any(k in q for k in explanation_keywords):
        return generate_concept_explanation(prompt, context)

    # Fallback open-ended response
    return generate_concept_explanation(prompt, context)


# ---------------------------------------------------------------------------
# AI FLASHCARDS & ACTIVE RECALL GENERATOR
# ---------------------------------------------------------------------------
def generate_ai_flashcards(user_id: int, topic: str = "", subject_id: int = None) -> list:
    """Generate high-yield revision flashcards for any subject or topic."""
    # Resolve subject name if subject_id provided
    if subject_id and not topic:
        subj = query_db("SELECT name, code FROM subjects WHERE id = ?", (subject_id,), one=True)
        if subj:
            topic = subj['name']

    topic_clean = topic.strip() if topic else "Computer Science & Engineering"
    t_low = topic_clean.lower()

    # Built-in High-Yield Curricular Flashcard Decks
    if any(k in t_low for k in ["data structure", "dsa", "algorithm", "bst", "array", "tree", "graph"]):
        return [
            {
                "id": 1,
                "front": "What is the average and worst-case time complexity of QuickSort?",
                "back": "Average: O(n log n). Worst Case: O(n²) when the chosen pivot is always the smallest or largest element (can be mitigated with randomized pivots).",
                "difficulty": "Intermediate",
                "tag": "Algorithms"
            },
            {
                "id": 2,
                "front": "What is the key difference between BFS (Breadth-First Search) and DFS (Depth-First Search)?",
                "back": "BFS explores neighbors level-by-level using a FIFO Queue (ideal for shortest path on unweighted graphs). DFS explores as deep as possible along each branch using a LIFO Stack or recursion.",
                "difficulty": "Fundamental",
                "tag": "Graph Theory"
            },
            {
                "id": 3,
                "front": "Why is lookup in a Hash Table O(1) average, and what happens during a collision?",
                "back": "A hash function computes array indices in O(1) time. Collisions occur when two keys map to the same bucket; handled via Separate Chaining (linked lists) or Open Addressing (linear probing).",
                "difficulty": "Fundamental",
                "tag": "Hash Tables"
            },
            {
                "id": 4,
                "front": "What is the invariant property of a Binary Search Tree (BST)?",
                "back": "For every node: all values in its Left subtree are strictly LESS, and all values in its Right subtree are strictly GREATER than the node's value. In-order traversal yields sorted order.",
                "difficulty": "Fundamental",
                "tag": "Trees"
            },
            {
                "id": 5,
                "front": "What is the two-pointer technique and when is it optimal?",
                "back": "Using two indices (start and end, or fast and slow) moving inwards or simultaneously. Achieves O(n) time and O(1) space for palindromes, 2-Sum sorted arrays, and cycle detection.",
                "difficulty": "Advanced",
                "tag": "Patterns"
            }
        ]

    if any(k in t_low for k in ["database", "dbms", "sql", "nosql"]):
        return [
            {
                "id": 1,
                "front": "What are the four ACID properties in relational databases?",
                "back": "Atomicity (all-or-nothing), Consistency (rules/constraints enforced), Isolation (concurrent transactions don't interfere), Durability (committed data survives crashes).",
                "difficulty": "Fundamental",
                "tag": "Transactions"
            },
            {
                "id": 2,
                "front": "What is Database Normalization and why is 3NF used?",
                "back": "Organizing tables to reduce redundant data and prevent insert/update/delete anomalies. 3NF ensures every non-key column depends strictly on the primary key, whole key, and nothing but the key.",
                "difficulty": "Intermediate",
                "tag": "Schema Design"
            },
            {
                "id": 3,
                "front": "What is a B-Tree Index and how does it speed up SQL queries?",
                "back": "A self-balancing search tree keeping data sorted in blocks. Reduces search complexity from full table scan O(n) to O(log n) disk reads for range queries and equality lookups.",
                "difficulty": "Advanced",
                "tag": "Indexing"
            },
            {
                "id": 4,
                "front": "What is the difference between an INNER JOIN and a LEFT JOIN?",
                "back": "INNER JOIN returns only rows where a match exists in BOTH tables. LEFT JOIN returns ALL rows from the left table, with NULLs for unmatched right-table columns.",
                "difficulty": "Fundamental",
                "tag": "SQL Queries"
            },
            {
                "id": 5,
                "front": "When should you choose PostgreSQL/SQL over MongoDB/NoSQL?",
                "back": "Choose SQL for structured entities with foreign key relationships, financial integrity, and complex joins. Choose NoSQL for high write velocity, dynamic schemas, and horizontal sharding.",
                "difficulty": "Intermediate",
                "tag": "Architecture"
            }
        ]

    if any(k in t_low for k in ["operating system", "os", "architecture"]):
        return [
            {
                "id": 1,
                "front": "What is the core difference between a Process and a Thread?",
                "back": "A Process is an isolated running program with its own virtual address space. A Thread is a lightweight execution unit inside a process sharing code, data, and open files with other threads.",
                "difficulty": "Fundamental",
                "tag": "Concurrency"
            },
            {
                "id": 2,
                "front": "What four conditions must hold simultaneously for Deadlock to occur?",
                "back": "1. Mutual Exclusion\n2. Hold and Wait\n3. No Preemption\n4. Circular Wait (breaking any one prevents deadlock!).",
                "difficulty": "Intermediate",
                "tag": "Deadlocks"
            },
            {
                "id": 3,
                "front": "How does Virtual Memory and Paging work in modern OS?",
                "back": "The OS maps large virtual addresses to physical RAM frames via Page Tables and MMU. Inactive pages are temporarily swapped to disk; accessing an unmapped page triggers a Page Fault.",
                "difficulty": "Advanced",
                "tag": "Memory Management"
            },
            {
                "id": 4,
                "front": "What is the role of the CPU Scheduler (Preemptive vs Non-Preemptive)?",
                "back": "Preemptive (Round Robin, SRTF) can interrupt a running process to switch context to higher priority tasks. Non-preemptive (FCFS) lets the process run until it voluntarily yields or terminates.",
                "difficulty": "Intermediate",
                "tag": "Scheduling"
            },
            {
                "id": 5,
                "front": "What is a Race Condition and how do Mutexes prevent it?",
                "back": "Occurs when concurrent threads access shared data and the final outcome depends on execution timing. A Mutex (mutual exclusion lock) ensures only 1 thread enters the Critical Section at a time.",
                "difficulty": "Intermediate",
                "tag": "Synchronization"
            }
        ]

    # Default Academic Mastery Deck for Any Subject / Topic
    return [
        {
            "id": 1,
            "front": f"Core Definition: What is the primary purpose of {topic_clean}?",
            "back": f"{topic_clean} provides a structured framework and methodology to solve domain-specific problems efficiently while maintaining reliability, performance, and clear boundaries.",
            "difficulty": "Fundamental",
            "tag": topic_clean
        },
        {
            "id": 2,
            "front": f"Key Principle: What is the single most important rule or mechanism in {topic_clean}?",
            "back": "Separation of concerns and modularity: decompose complex requirements into smaller, independently verifiable units with well-defined inputs and expected outputs.",
            "difficulty": "Intermediate",
            "tag": "Mechanics"
        },
        {
            "id": 3,
            "front": f"Exam Trap: What common mistake or pitfall do students make when studying {topic_clean}?",
            "back": "Rote memorization without applying the concept to edge cases, boundary conditions, or timed practical problem sets.",
            "difficulty": "Intermediate",
            "tag": "Exam Strategy"
        },
        {
            "id": 4,
            "front": f"Trade-offs: What are the main advantages and constraints of {topic_clean}?",
            "back": "Advantage: High structural clarity and standardized patterns. Constraint: Added overhead or complexity if applied to overly simplistic scenarios.",
            "difficulty": "Advanced",
            "tag": "Analysis"
        },
        {
            "id": 5,
            "front": f"Active Recall: Can you explain the real-world utility of {topic_clean} in 60 seconds?",
            "back": "Practice testing yourself closed-book: state the Definition, 1 Real-World Analogy, and 1 Concrete Example out loud to lock it into long-term memory.",
            "difficulty": "Fundamental",
            "tag": "Retention"
        }
    ]

