"""
SportTracker Pro - Routes d'Authentification
=============================================
"""

from datetime import datetime, timedelta
import secrets

from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, Player
from app.forms import LoginForm, RegisterForm, ForgotPasswordForm, ResetPasswordForm

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion unifiée"""
    if current_user.is_authenticated:
        return redirect_by_role(current_user.role)

    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data.lower()
        password = form.password.data

        # Rechercher l'utilisateur par email
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if user.is_active:
                login_user(user)
                session['user_role'] = user.role

                flash(f'Bienvenue {user.first_name} !', 'success')
                return redirect_by_role(user.role)
            else:
                flash('Votre compte est désactivé.', 'danger')
        else:
            flash('Email ou mot de passe incorrect.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Page d'inscription (staff uniquement)"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegisterForm()

    if form.validate_on_submit():
        # Vérifier si l'email existe déjà
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash('Cet email est déjà utilisé.', 'danger')
            return render_template('auth/register.html', form=form)

        user = User(
            email=form.email.data.lower(),
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            role=form.role.data,
            phone=form.phone.data
        )
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.commit()

        flash('Compte créé avec succès ! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """Déconnexion"""
    logout_user()
    session.clear()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
@login_required
def profile():
    """Profil de l'utilisateur (joueur ou staff)"""
    from app.models import Player, TrainingResult, GPSData

    player = None
    stats = {
        'total_sessions': 0,
        'total_distance': 0,
        'best_distance': 0,
        'best_speed': 0,
        'accuracy': 100
    }

    # Si l'utilisateur est un joueur
    if current_user.player_id:
        player = Player.query.get(current_user.player_id)

        if player:
            # Calculer les statistiques
            total_sessions = TrainingResult.query.filter_by(player_id=player.id).count()
            total_distance = db.session.query(db.func.sum(GPSData.total_distance)).filter_by(
                player_id=player.id
            ).scalar() or 0

            best_distance = db.session.query(db.func.max(GPSData.total_distance)).filter_by(
                player_id=player.id
            ).scalar() or 0

            best_speed = db.session.query(db.func.max(GPSData.max_speed)).filter_by(
                player_id=player.id
            ).scalar() or 0

            # Calculer la précision (assiduité)
            accuracy = 100
            if total_sessions > 0:
                total_attendance = TrainingResult.query.filter_by(player_id=player.id, status='Completed').count()
                accuracy = round((total_attendance / total_sessions) * 100)

            stats = {
                'total_sessions': total_sessions,
                'total_distance': round(total_distance / 1000, 1) if total_distance else 0,
                'best_distance': round(best_distance, 0) if best_distance else 0,
                'best_speed': round(best_speed, 1) if best_speed else 0,
                'accuracy': accuracy
            }
    else:
        # Pour les staff, créer un objet Player minimal avec les infos du User
        player = current_user
        # Ajouter les attributs manquants pour compatibilité avec le template
        if not hasattr(player, 'date_of_birth'):
            player.date_of_birth = None
        if not hasattr(player, 'position'):
            player.position = player.role_display
        if not hasattr(player, 'jersey_number'):
            player.jersey_number = None
        if not hasattr(player, 'height'):
            player.height = None
        if not hasattr(player, 'weight'):
            player.weight = None
        if not hasattr(player, 'dominant_foot'):
            player.dominant_foot = None
        if not hasattr(player, 'status'):
            player.status = 'Actif' if player.is_active else 'Inactif'
        if not hasattr(player, 'team'):
            player.team = None
        if not hasattr(player, 'age'):
            player.age = '-'
        if not hasattr(player, 'bmi'):
            player.bmi = None
        if not hasattr(player, 'hr_max'):
            player.hr_max = None
        if not hasattr(player, 'vma'):
            player.vma = None
        if not hasattr(player, 'injuries'):
            player.injuries = []
        if not hasattr(player, 'wellness_records'):
            player.wellness_records = []

    return render_template('auth/profile.html', player=player, stats=stats)


# =============================================================================
# RESET PASSWORD (Etape 2 - Securite)
# =============================================================================

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Demande de reinitialisation du mot de passe."""
    if current_user.is_authenticated:
        return redirect_by_role(current_user.role)

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            # Generer un token securise et le stocker
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()

            # Construire le lien de reset
            reset_url = url_for('auth.reset_password', token=token, _external=True)

            # En mode dev : afficher le lien dans la console
            # En production : envoyer par e-mail (Flask-Mail)
            current_app.logger.info(f"[RESET-PASSWORD] Lien pour {user.email} : {reset_url}")
            print(f"\n=== LIEN DE REINITIALISATION ===\n{reset_url}\n=================================\n")

            flash(
                "Un lien de reinitialisation a ete genere. "
                "En developpement, consultez la console du serveur. "
                "En production, il sera envoye par email.",
                'success'
            )
        else:
            # Anti-enumeration : meme message si l'email existe ou non
            flash(
                "Si cet email existe, un lien de reinitialisation a ete envoye.",
                'info'
            )
        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html', form=form)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reinitialisation du mot de passe via un token."""
    if current_user.is_authenticated:
        return redirect_by_role(current_user.role)

    # Verifier le token
    user = User.query.filter_by(reset_token=token).first()
    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
        flash("Lien invalide ou expire. Veuillez refaire une demande.", 'danger')
        return redirect(url_for('auth.forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.reset_token = None
        user.reset_token_expires = None
        db.session.commit()
        flash("Mot de passe reinitialise avec succes. Vous pouvez vous connecter.", 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', form=form, token=token)


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================


def redirect_by_role(role):
    """Redirige vers la page appropriée selon le rôle"""
    redirects = {
        'admin': 'dashboard.admin',
        'coach': 'dashboard.coach',
        'assistant': 'dashboard.coach',
        'preparateur': 'dashboard.preparateur',
        'medical': 'medical.dashboard',
        'analyst': 'dashboard.analyst',
        'player': 'player_portal.dashboard',
        'dirigeant': 'dashboard.dirigeant'
    }

    endpoint = redirects.get(role, 'main.index')

    try:
        return redirect(url_for(endpoint))
    except:
        return redirect(url_for('main.index'))
