"""
SportTracker Pro - Configuration
================================
"""

import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Configuration de base"""
    
    # Clé secrète
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'sporttracker-pro-secret-key-2025'
    
    # Base de données
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload de fichiers GPS
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads', 'gps')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB max
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'json', 'xml'}
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # Pagination
    ITEMS_PER_PAGE = 20
    
    # Seuils GPS (valeurs par défaut)
    GPS_SPEED_ZONE_1 = 6.0    # km/h
    GPS_SPEED_ZONE_2 = 12.0
    GPS_SPEED_ZONE_3 = 18.0
    GPS_SPEED_ZONE_4 = 21.0
    GPS_SPEED_ZONE_5 = 24.0
    GPS_HSR_THRESHOLD = 19.8  # km/h
    GPS_SPRINT_THRESHOLD = 25.2  # km/h
    
    # Seuils d'alerte
    ACWR_WARNING = 1.3
    ACWR_DANGER = 1.5
    TSB_WARNING = -10
    TSB_DANGER = -20
    WELLNESS_WARNING = 15
    WELLNESS_DANGER = 10
    
    # Configuration Email (Flask-Mail)
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', True)
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')  # email@gmail.com
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')  # app password
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@sporttrackerpro.com'
    
    # Pour développement: mode offline email (affiche logs)
    TESTING_MAIL = os.environ.get('TESTING_MAIL', False)
    
    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    """Configuration de développement"""
    
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'sporttracker_pro.db')


class ProductionConfig(Config):
    """Configuration de production"""
    
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://user:password@localhost/sporttracker_pro'
    
    # Supabase (optionnel)
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')


class TestingConfig(Config):
    """Configuration de test"""
    
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
