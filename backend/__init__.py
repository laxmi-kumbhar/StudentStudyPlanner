import os
from flask import Flask
from backend.config import config_by_name
from database.db import init_app, init_db

def create_app(config_name=None):
    """Application factory for Student Study Planner."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
        
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'templates'),
        static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'static')
    )
    
    app.config.from_object(config_by_name[config_name])
    
    # Initialize database hooks
    init_app(app)
    
    # Enable CORS for frontend clients (e.g. VS Code Live Server on port 5500)
    @app.before_request
    def handle_preflight():
        from flask import request, make_response
        if request.method == 'OPTIONS':
            res = make_response()
            origin = request.headers.get('Origin', '*')
            res.headers['Access-Control-Allow-Origin'] = origin
            res.headers['Access-Control-Allow-Credentials'] = 'true'
            res.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
            res.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS,PATCH'
            return res

    @app.after_request
    def add_cors_headers(response):
        from flask import request
        origin = request.headers.get('Origin')
        if origin:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
        else:
            response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS,PATCH'
        return response

    @app.before_request
    def enforce_auth_globally():
        from flask import request, session, redirect, url_for, jsonify
        if request.method == 'OPTIONS':
            return None
            
        path = request.path
        # Whitelist static assets and auth endpoints
        if path.startswith('/static/') or path.startswith('/api/auth/') or path in ['/login', '/register', '/logout', '/favicon.ico']:
            return None
            
        if not session.get('user_id'):
            if path.startswith('/api/'):
                return jsonify({"success": False, "error": "Unauthorized. Please log in."}), 401
            return redirect(url_for('views.login'))

    # Ensure database file exists on startup
    db_path = app.config['DATABASE']
    if not os.path.exists(db_path):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        init_db(app.config['SCHEMA'])
    
    # Register blueprints
    from backend.routes.view_routes import views_bp
    from backend.routes.auth_routes import auth_bp
    from backend.routes.subject_routes import subject_bp
    from backend.routes.task_routes import task_bp
    from backend.routes.timer_routes import timer_bp
    from backend.routes.calendar_routes import calendar_bp
    from backend.routes.analytics_routes import analytics_bp
    from backend.routes.ai_routes import ai_bp
    
    app.register_blueprint(views_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(subject_bp)
    app.register_blueprint(task_bp)
    app.register_blueprint(timer_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(ai_bp)
    
    return app
