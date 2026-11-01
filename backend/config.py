import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
load_dotenv(os.path.join(BASE_DIR, '.env'))

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'super-secret-study-planner-key-2026')
    DATABASE = os.path.join(BASE_DIR, 'database', 'study_planner.db')
    SCHEMA = os.path.join(BASE_DIR, 'database', 'schema.sql')
    
    # Template and Static folder paths in frontend/
    TEMPLATE_FOLDER = os.path.join(BASE_DIR, 'frontend', 'templates')
    STATIC_FOLDER = os.path.join(BASE_DIR, 'frontend', 'static')
    
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024 # 16 MB max

    # Google OAuth / Sign-In Configuration
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '').strip()

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
