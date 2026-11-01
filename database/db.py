import sqlite3
import os
from flask import g, current_app

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'study_planner.db')

def get_db_path():
    """Return database file path from Flask app config or default."""
    try:
        return current_app.config.get('DATABASE', DEFAULT_DB_PATH)
    except RuntimeError:
        # If called outside Flask application context
        return os.environ.get('DATABASE_PATH', DEFAULT_DB_PATH)

def get_db():
    """Open a unique database connection per request and set row_factory."""
    if 'db' not in g:
        db_path = get_db_path()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        g.db = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

def close_db(e=None):
    """Close the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    """Convenience helper to query the database and return dictionary rows."""
    db = get_db()
    cur = db.execute(query, args)
    rv = [dict(row) for row in cur.fetchall()]
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    """Helper to execute an INSERT/UPDATE/DELETE query and commit."""
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    last_id = cur.lastrowid
    row_count = cur.rowcount
    cur.close()
    return {"lastrowid": last_id, "rowcount": row_count}

def init_db(schema_path=None):
    """Initialize database from schema.sql."""
    if schema_path is None:
        schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')
    
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    with open(schema_path, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print(f"Database initialized successfully at: {db_path}")

def migrate_schema(conn=None):
    """Ensure newer columns (e.g. for Google OAuth) exist in older SQLite databases."""
    should_close = False
    if conn is None:
        db_path = get_db_path()
        if not os.path.exists(db_path):
            return
        conn = sqlite3.connect(db_path)
        should_close = True
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        cols = {row[1] for row in cur.fetchall()}
        if 'auth_provider' not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN auth_provider TEXT DEFAULT 'local'")
        if 'google_id' not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN google_id TEXT")
        if 'avatar_url' not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")
        conn.commit()
    except Exception as e:
        print(f"Database schema migration note: {e}")
    finally:
        if should_close and conn:
            conn.close()

def init_app(app):
    """Register database functions with Flask app."""
    app.teardown_appcontext(close_db)
    with app.app_context():
        migrate_schema()
