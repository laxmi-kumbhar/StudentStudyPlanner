import os
import re
import json
import secrets
import urllib.request
import urllib.parse
from flask import Blueprint, request, jsonify, session, current_app, redirect, url_for
from backend.utils.auth_helpers import (
    hash_password, verify_password, get_current_user_id, get_current_user,
    is_valid_email, seed_starter_data_for_user
)
from database.db import query_db, execute_db

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user with Gmail / email and password."""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not username:
        return jsonify({"success": False, "error": "Username is required."}), 400
    if not email:
        return jsonify({"success": False, "error": "Gmail or Email address is required."}), 400
    if not is_valid_email(email):
        return jsonify({"success": False, "error": "Please provide a valid Gmail or email address (e.g. name@gmail.com)."}), 400
    if not password or len(password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters long."}), 400
    
    # Check if username or email already exists (case-insensitive)
    existing_user = query_db(
        "SELECT id, username, email FROM users WHERE LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?)",
        (username, email),
        one=True
    )
    if existing_user:
        if existing_user['email'].lower() == email:
            return jsonify({"success": False, "error": "This Gmail / email address is already registered. Please sign in."}), 409
        return jsonify({"success": False, "error": "This username is already taken. Please choose another."}), 409
    
    pwd_hash = hash_password(password)
    res = execute_db("""
        INSERT INTO users (username, email, password_hash, auth_provider, avatar_color, daily_goal_minutes)
        VALUES (?, ?, ?, 'local', ?, ?)
    """, (username, email, pwd_hash, '#6366f1', 120))
    
    user_id = res['lastrowid']
    seed_starter_data_for_user(user_id)
    
    session['user_id'] = user_id
    session['username'] = username
    
    return jsonify({
        "success": True,
        "message": "Account created successfully! Welcome to StudyFlow.",
        "user_id": user_id,
        "username": username
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    """Sign in with Gmail / email ID and password (or username)."""
    data = request.get_json() or {}
    login_id = data.get('username', '').strip() # can be Gmail address, email or username
    password = data.get('password', '')
    
    if not login_id:
        return jsonify({"success": False, "error": "Please enter your Gmail / email ID or username."}), 400
    if not password:
        return jsonify({"success": False, "error": "Please enter your password."}), 400
    
    # Query case-insensitively for either email or username
    user = query_db(
        "SELECT * FROM users WHERE LOWER(email) = LOWER(?) OR LOWER(username) = LOWER(?)",
        (login_id, login_id),
        one=True
    )
    
    if not user:
        return jsonify({
            "success": False,
            "error": f"No account found for '{login_id}'. Please click 'Create Account' below to register your account first!",
            "suggest_register": True,
            "email": login_id if "@" in login_id else ""
        }), 401
    
    if not user.get('password_hash') or not verify_password(password, user['password_hash']):
        if user.get('auth_provider') == 'google':
            return jsonify({
                "success": False,
                "error": "This account was created with Google Sign-In. Please click 'Sign in with Google'."
            }), 401
        return jsonify({"success": False, "error": "Incorrect password. Please try again."}), 401
    
    session['user_id'] = user['id']
    session['username'] = user['username']
    
    return jsonify({
        "success": True,
        "message": f"Welcome back, {user['username']}!",
        "username": user['username'],
        "user_id": user['id']
    })

@auth_bp.route('/google', methods=['POST'])
def google_auth():
    """Handle Sign-In with Google via Google Identity Services ID Token."""
    data = request.get_json() or {}
    credential = data.get('credential') or data.get('id_token')
    
    if not credential:
        return jsonify({"success": False, "error": "Missing Google authentication credential."}), 400
    
    configured_client_id = current_app.config.get('GOOGLE_CLIENT_ID', '').strip()
    
    # Verify the credential with Google's official tokeninfo endpoint
    try:
        verify_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={urllib.parse.quote(credential)}"
        req = urllib.request.Request(verify_url, headers={'User-Agent': 'StudentStudyPlanner/2.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to verify Google credential with Google servers: {str(e)}"}), 401
    
    google_id = payload.get('sub')
    email = payload.get('email', '').strip().lower()
    name = payload.get('name', '').strip()
    picture = payload.get('picture', '')
    audience = payload.get('aud', '')
    
    if not email:
        return jsonify({"success": False, "error": "Unable to retrieve verified email from Google."}), 400
        
    if configured_client_id and audience != configured_client_id:
        return jsonify({"success": False, "error": "Google token audience mismatch with configured Google Client ID."}), 401

    # Look for existing user by google_id or email
    user = query_db(
        "SELECT * FROM users WHERE google_id = ? OR LOWER(email) = LOWER(?)",
        (google_id, email),
        one=True
    )
    
    if user:
        # Existing user - update google_id and avatar if needed
        execute_db("""
            UPDATE users SET google_id = COALESCE(google_id, ?), avatar_url = COALESCE(avatar_url, ?)
            WHERE id = ?
        """, (google_id, picture, user['id']))
        user_id = user['id']
        username = user['username']
    else:
        # New Google user - create user account
        base_username = (name.replace(' ', '_').lower() if name else email.split('@')[0])
        # Clean username of non-alphanumeric chars
        base_username = ''.join(c for c in base_username if c.isalnum() or c in ('_', '-')) or 'student'
        candidate_username = base_username
        
        counter = 1
        while query_db("SELECT id FROM users WHERE LOWER(username) = LOWER(?)", (candidate_username,), one=True):
            candidate_username = f"{base_username}_{counter}"
            counter += 1
            
        random_pwd = hash_password(secrets.token_hex(20))
        res = execute_db("""
            INSERT INTO users (username, email, password_hash, auth_provider, google_id, avatar_url, avatar_color, daily_goal_minutes)
            VALUES (?, ?, ?, 'google', ?, ?, '#4285F4', 120)
        """, (candidate_username, email, random_pwd, google_id, picture))
        
        user_id = res['lastrowid']
        username = candidate_username
        seed_starter_data_for_user(user_id)
        
    session['user_id'] = user_id
    session['username'] = username
    
    return jsonify({
        "success": True,
        "message": f"Signed in with Google as {email}!",
        "username": username,
        "user_id": user_id
    })

@auth_bp.route('/google/direct', methods=['POST'])
def google_direct_login():
    """Sign in directly with user's own Google account email and name."""
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    full_name = data.get('name', '').strip()
    
    if not email:
        return jsonify({"success": False, "error": "Please enter your Gmail / Google account email."}), 400
    if not is_valid_email(email):
        return jsonify({"success": False, "error": "Please enter a valid Gmail address (e.g. student@gmail.com)."}), 400
        
    display_name = full_name or email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
    
    # Check if user already exists with this email
    user = query_db("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email,), one=True)
    if not user:
        # Generate clean unique username
        base_username = re.sub(r'[^a-zA-Z0-9_]', '_', email.split('@')[0])[:20] or "student"
        username = base_username
        counter = 1
        while query_db("SELECT id FROM users WHERE LOWER(username) = LOWER(?)", (username,), one=True):
            username = f"{base_username}_{counter}"
            counter += 1
            
        random_pwd = hash_password(secrets.token_hex(24))
        google_id = f"custom_google_{email}"
        res = execute_db("""
            INSERT INTO users (username, email, password_hash, auth_provider, google_id, avatar_color, daily_goal_minutes)
            VALUES (?, ?, ?, 'google', ?, '#4285F4', 150)
        """, (username, email, random_pwd, google_id))
        user_id = res['lastrowid']
        seed_starter_data_for_user(user_id)
    else:
        user_id = user['id']
        username = user['username']
        
    session['user_id'] = user_id
    session['username'] = username
    
    return jsonify({
        "success": True,
        "message": f"Welcome, {display_name}!",
        "username": username,
        "user_id": user_id
    })

@auth_bp.route('/google/demo', methods=['POST'])
def google_demo_login():
    """Quick demo Google account login for instant testing before setting up Google Cloud Console."""
    demo_email = "student.google@gmail.com"
    demo_name = "Google Student"
    google_id = "demo_google_student_101"
    picture = "https://lh3.googleusercontent.com/a/default-user=s96-c"
    
    user = query_db("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (demo_email,), one=True)
    if not user:
        random_pwd = hash_password(secrets.token_hex(20))
        res = execute_db("""
            INSERT INTO users (username, email, password_hash, auth_provider, google_id, avatar_url, avatar_color, daily_goal_minutes)
            VALUES (?, ?, ?, 'google', ?, ?, '#4285F4', 150)
        """, ("google_student", demo_email, random_pwd, google_id, picture))
        user_id = res['lastrowid']
        username = "google_student"
        seed_starter_data_for_user(user_id)
    else:
        user_id = user['id']
        username = user['username']
        
    session['user_id'] = user_id
    session['username'] = username
    
    return jsonify({
        "success": True,
        "message": "Signed in with Demo Google Account (student.google@gmail.com)!",
        "username": username,
        "user_id": user_id
    })

@auth_bp.route('/demo', methods=['POST'])
def quick_demo_login():
    """Quick login as the pre-seeded demo user (alex_student) with full sample schedule & statistics."""
    user = query_db("SELECT * FROM users WHERE username = 'alex_student' OR id = 1 LIMIT 1", one=True)
    if not user:
        # Auto-create demo user if missing on clean cloud deployment
        demo_password_hash = hash_password("password123")
        res = execute_db("""
            INSERT INTO users (username, email, password_hash, auth_provider, avatar_color, daily_goal_minutes)
            VALUES ('alex_student', 'alex@study.edu', ?, 'local', '#6366f1', 180)
        """, (demo_password_hash,))
        user_id = res['lastrowid']
        seed_starter_data_for_user(user_id)
        user = {'id': user_id, 'username': 'alex_student'}
        
    session['user_id'] = user['id']
    session['username'] = user['username']
    
    return jsonify({
        "success": True,
        "message": f"Logged in as demo user ({user['username']})!",
        "username": user['username'],
        "user_id": user['id']
    })

@auth_bp.route('/logout', methods=['POST', 'GET'])
def logout():
    """Clear session and log out."""
    session.clear()
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({"success": True, "message": "Logged out successfully."})
    return redirect(url_for('views.login'))

@auth_bp.route('/me', methods=['GET'])
def me():
    """Get current authenticated user info."""
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "error": "Not authenticated"}), 401
    return jsonify({"success": True, "user": user})

@auth_bp.route('/profile', methods=['PUT'])
def update_profile():
    """Update profile settings (daily study goal, avatar color)."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"success": False, "error": "Not authenticated"}), 401
        
    data = request.get_json() or {}
    daily_goal = data.get('daily_goal_minutes', 120)
    avatar_color = data.get('avatar_color', '#6366f1')
    
    execute_db("""
        UPDATE users SET daily_goal_minutes = ?, avatar_color = ? WHERE id = ?
    """, (daily_goal, avatar_color, user_id))
    
    return jsonify({"success": True, "message": "Profile updated successfully!"})
