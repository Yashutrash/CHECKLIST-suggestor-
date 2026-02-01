import os
from datetime import timedelta

class Config:
    """Base configuration class."""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_ENV') == 'development'
    
    # Database Configuration
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'sqlite:///users.db'
    
    # CORS Configuration
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
    
    # AI/ML Configuration
    MODEL_PATH = os.environ.get('MODEL_PATH') or 'models/'
    SUGGESTION_CONFIDENCE_THRESHOLD = float(os.environ.get('SUGGESTION_CONFIDENCE_THRESHOLD', 0.7))
    
    # Analytics Configuration
    TREND_ANALYSIS_DAYS = int(os.environ.get('TREND_ANALYSIS_DAYS', 30))
    COMMON_ISSUES_LIMIT = int(os.environ.get('COMMON_ISSUES_LIMIT', 10))
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'app.log')
    
    # Security Configuration
    PASSWORD_MIN_LENGTH = int(os.environ.get('PASSWORD_MIN_LENGTH', 8))
    SESSION_TIMEOUT = int(os.environ.get('SESSION_TIMEOUT', 3600))  # 1 hour
    
    # Rate Limiting
    RATE_LIMIT_ENABLED = os.environ.get('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
    RATE_LIMIT_REQUESTS = int(os.environ.get('RATE_LIMIT_REQUESTS', 100))
    RATE_LIMIT_WINDOW = int(os.environ.get('RATE_LIMIT_WINDOW', 3600))  # 1 hour

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    FLASK_ENV = 'development'
    
class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    FLASK_ENV = 'production'
    SESSION_COOKIE_SECURE = True
    
    # Production security settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    
class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    DATABASE_URL = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on environment."""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])

# Environment-specific settings
def get_database_url():
    """Get database URL based on environment."""
    if os.environ.get('FLASK_ENV') == 'production':
        return os.environ.get('DATABASE_URL')
    return 'sqlite:///users.db'

def get_secret_key():
    """Get secret key based on environment."""
    if os.environ.get('FLASK_ENV') == 'production':
        return os.environ.get('SECRET_KEY')
    return 'dev-secret-key-change-in-production'

# Feature flags
FEATURE_FLAGS = {
    'ai_suggestions': os.environ.get('ENABLE_AI_SUGGESTIONS', 'true').lower() == 'true',
    'analytics': os.environ.get('ENABLE_ANALYTICS', 'true').lower() == 'true',
    'file_upload': os.environ.get('ENABLE_FILE_UPLOAD', 'true').lower() == 'true',
    'export': os.environ.get('ENABLE_EXPORT', 'true').lower() == 'true',
    'real_time': os.environ.get('ENABLE_REAL_TIME', 'false').lower() == 'true',
}

# API Configuration
API_CONFIG = {
    'version': '1.0.0',
    'title': 'AI Checklist Suggestion Tool API',
    'description': 'API for AI-powered checklist suggestion tool',
    'contact': {
        'name': 'API Support',
        'email': 'support@example.com'
    },
    'license': {
        'name': 'MIT',
        'url': 'https://opensource.org/licenses/MIT'
    }
}

# AI Model Configuration
AI_CONFIG = {
    'model_type': os.environ.get('AI_MODEL_TYPE', 'pattern_recognition'),
    'confidence_threshold': float(os.environ.get('AI_CONFIDENCE_THRESHOLD', 0.7)),
    'max_suggestions': int(os.environ.get('AI_MAX_SUGGESTIONS', 10)),
    'training_data_path': os.environ.get('AI_TRAINING_DATA_PATH', 'data/mock_inspection_data.csv'),
    'model_save_path': os.environ.get('AI_MODEL_SAVE_PATH', 'models/'),
}

# Analytics Configuration
ANALYTICS_CONFIG = {
    'trend_analysis_days': int(os.environ.get('ANALYTICS_TREND_DAYS', 30)),
    'common_issues_limit': int(os.environ.get('ANALYTICS_ISSUES_LIMIT', 10)),
    'dashboard_refresh_interval': int(os.environ.get('ANALYTICS_REFRESH_INTERVAL', 300)),  # 5 minutes
    'export_formats': ['csv', 'xlsx', 'json'],
    'chart_types': ['line', 'bar', 'pie', 'scatter'],
} 