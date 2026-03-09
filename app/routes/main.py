"""
SportTracker Pro - Routes Principales
=====================================
"""

from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Page d'accueil - Portfolio ou redirection selon statut"""
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
    
    # Afficher le portfolio pour les utilisateurs non connectés
    return render_template('portfolio.html')


@main_bp.route('/portfolio')
def portfolio():
    """Page portfolio - Présentation de la plateforme"""
    return render_template('portfolio.html')


@main_bp.route('/about')
def about():
    """Page À propos"""
    return render_template('about.html')


@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Page de contact"""
    return render_template('contact.html')


@main_bp.route('/documentation')
def documentation():
    """Page de documentation"""
    return render_template('documentation.html')


@main_bp.route('/support')
def support():
    """Page d'assistance et FAQ"""
    return render_template('support.html')


@main_bp.route('/terms')
def terms():
    """Conditions d'utilisation"""
    return render_template('terms.html')


@main_bp.route('/privacy')
def privacy():
    """Politique de confidentialité"""
    return render_template('privacy.html')
