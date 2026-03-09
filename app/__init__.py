"""
SportTracker Pro - Application Factory
=======================================
"""

import os
from flask import Flask, session, send_from_directory
from flask_login import LoginManager
from config import config
from app.models import db, User
from app.services import mail

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
login_manager.login_message_category = 'warning'


def create_app(config_name='default'):
    """Factory pattern pour créer l'application Flask"""
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Initialisation des extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    
    # Créer le dossier instance si nécessaire
    instance_path = os.path.join(os.path.dirname(app.root_path), 'instance')
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
    
    # Créer le dossier uploads si nécessaire
    uploads_path = app.config.get('UPLOAD_FOLDER')
    if uploads_path and not os.path.exists(uploads_path):
        os.makedirs(uploads_path)
    
    # Créer le dossier uploads/players pour les photos de profil
    players_uploads_path = os.path.join(os.path.dirname(app.root_path), 'uploads', 'players')
    if not os.path.exists(players_uploads_path):
        os.makedirs(players_uploads_path)
    
    # User loader pour Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Enregistrement des Blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.players import players_bp
    from app.routes.teams import teams_bp
    from app.routes.sessions import sessions_bp
    from app.routes.gps import gps_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.player_portal import player_portal_bp
    from app.routes.medical import medical_bp
    from app.routes.api import api_bp
    from app.routes.exports import export_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(players_bp, url_prefix='/players')
    app.register_blueprint(teams_bp, url_prefix='/teams')
    app.register_blueprint(sessions_bp, url_prefix='/sessions')
    app.register_blueprint(gps_bp, url_prefix='/gps')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(player_portal_bp, url_prefix='/player')
    app.register_blueprint(medical_bp, url_prefix='/medical')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(export_bp)
    
    # Route pour servir les fichiers uploadés
    base_uploads_path = os.path.join(os.path.dirname(app.root_path), 'uploads')
    
    @app.route('/uploads/<path:filepath>')
    def serve_uploads(filepath):
        """Servir les fichiers uploadés (photos, GPS, etc.)"""
        return send_from_directory(base_uploads_path, filepath)
    
    # Context processor pour les templates
    @app.context_processor
    def inject_globals():
        return {
            'app_name': 'SportTracker Pro',
            'app_version': '2.0',
            'current_user_role': session.get('user_role', 'guest')
        }
    
    # Création des tables
    with app.app_context():
        db.create_all()
    
    return app
