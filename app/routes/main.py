"""
SportTracker Pro - Routes Principales
=====================================
"""

from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Page d'accueil - Redirige selon le statut de connexion"""
    if current_user.is_authenticated:
        # Rediriger vers le dashboard approprié selon le rôle
        role = current_user.role
        
        if role == 'player':
            return redirect(url_for('player_portal.dashboard'))
        elif role == 'medical':
            return redirect(url_for('medical.dashboard'))
        elif role == 'admin':
            return redirect(url_for('dashboard.admin'))
        else:
            return redirect(url_for('dashboard.coach'))
    
    return redirect(url_for('auth.login'))


@main_bp.route('/about')
def about():
    """Page À propos"""
    return render_template('shared/about.html')
