"""
RajaTracker - Routes d'Authentification
=============================================
"""

from datetime import datetime, timedelta
import secrets
import io
import base64

import pyotp
import qrcode

from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, Player, log_action
from app import limiter
from app.forms import LoginForm, RegisterForm, ForgotPasswordForm, ResetPasswordForm

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# =============================================================================
# LOGIN / LOGOUT / REGISTER
# =============================================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('5 per 15 minutes', methods=['POST'])
def login():
    """Page de connexion unifiée (avec gestion 2FA et journal d'audit)"""
    if current_user.is_authenticated:
        return redirect_by_role(current_user.role)

    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data.lower()
        password = form.password.data

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if not user.is_active:
                log_action('login_blocked_inactive', target_type='user',
                           target_id=user.id, target_name=user.email, user=user)
                flash('Votre compte est désactivé.', 'danger')
                return render_template('auth/login.html', form=form)

            # 2FA OBLIGATOIRE pour tous les utilisateurs
            if user.totp_enabled:
                # 2FA deja activee : rediriger vers verification du code
                session['pre_2fa_user_id'] = user.id
                log_action('login_2fa_required', target_type='user',
                           target_id=user.id, target_name=user.email, user=user)
                return redirect(url_for('auth.verify_2fa'))
            else:
                # 2FA pas encore activee : forcer la configuration
                session['pre_2fa_user_id'] = user.id
                session['must_setup_2fa'] = True
                log_action('login_2fa_setup_required', target_type='user',
                           target_id=user.id, target_name=user.email, user=user)
                flash("Bienvenue ! Pour proteger votre compte, vous devez activer l'authentification a 2 facteurs.", 'info')
                return redirect(url_for('auth.setup_2fa'))
        else:
            # Echec : on log meme si user inexistant (sans crash)
            log_action('login_failed', target_type='user',
                       target_name=email, details=f"email tente: {email}")
            flash('Email ou mot de passe incorrect.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Page d'inscription (staff uniquement)"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegisterForm()

    if form.validate_on_submit():
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

        log_action('user_registered', target_type='user',
                   target_id=user.id, target_name=user.email, user=user)
        flash('Compte créé avec succès ! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """Déconnexion"""
    log_action('logout', target_type='user',
               target_id=current_user.id, target_name=current_user.email)
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

    if current_user.player_id:
        player = Player.query.get(current_user.player_id)

        if player:
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
        player = current_user
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
@limiter.limit('3 per hour', methods=['POST'])
def forgot_password():
    """Demande de reinitialisation du mot de passe."""
    if current_user.is_authenticated:
        return redirect_by_role(current_user.role)

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()

            reset_url = url_for('auth.reset_password', token=token, _external=True)
            current_app.logger.info(f"[RESET-PASSWORD] Lien pour {user.email} : {reset_url}")
            print(f"\n=== LIEN DE REINITIALISATION ===\n{reset_url}\n=================================\n")

            log_action('password_reset_requested', target_type='user',
                       target_id=user.id, target_name=user.email, user=user)

            flash(
                "Un lien de reinitialisation a ete genere. "
                "En developpement, consultez la console du serveur. "
                "En production, il sera envoye par email.",
                'success'
            )
        else:
            log_action('password_reset_requested_unknown_email',
                       target_name=form.email.data.lower())
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

    user = User.query.filter_by(reset_token=token).first()
    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
        log_action('password_reset_invalid_token', details=f"token={token[:8]}...")
        flash("Lien invalide ou expire. Veuillez refaire une demande.", 'danger')
        return redirect(url_for('auth.forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.reset_token = None
        user.reset_token_expires = None
        db.session.commit()
        log_action('password_reset_success', target_type='user',
                   target_id=user.id, target_name=user.email, user=user)
        flash("Mot de passe reinitialise avec succes. Vous pouvez vous connecter.", 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', form=form, token=token)


# =============================================================================
# 2FA / TOTP (Etape 2 - Securite)
# =============================================================================

@auth_bp.route('/setup-2fa', methods=['GET', 'POST'])
def setup_2fa():
    """
    Activer la 2FA : QR code + verification d'un premier code.
    Accessible :
    - Si l'utilisateur est deja connecte (renforcement volontaire)
    - Si l'utilisateur vient de saisir son mot de passe correct mais n'a pas encore active la 2FA (pre_2fa_user_id en session)
    """
    # Cas 1 : utilisateur deja connecte
    if current_user.is_authenticated:
        user = current_user
    # Cas 2 : utilisateur en cours de premier login (force par 2FA obligatoire)
    elif session.get('pre_2fa_user_id'):
        user = User.query.get(session['pre_2fa_user_id'])
        if not user:
            return redirect(url_for('auth.login'))
    else:
        return redirect(url_for('auth.login'))

    if user.totp_enabled:
        flash("La 2FA est deja activee sur votre compte.", 'info')
        if current_user.is_authenticated:
            return redirect(url_for('auth.profile'))
        return redirect(url_for('auth.verify_2fa'))

    if not user.totp_secret:
        user.totp_secret = pyotp.random_base32()
        db.session.commit()

    totp = pyotp.TOTP(user.totp_secret)
    provisioning_uri = totp.provisioning_uri(
        name=user.email,
        issuer_name='RajaTracker'
    )

    img = qrcode.make(provisioning_uri)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_base64 = base64.b64encode(buf.getvalue()).decode()

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        if totp.verify(code):
            user.totp_enabled = True
            db.session.commit()
            log_action('2fa_enabled', target_type='user',
                       target_id=user.id, target_name=user.email, user=user)

            # Si setup obligatoire post-login : on connecte l'utilisateur maintenant
            if session.get('must_setup_2fa'):
                session.pop('must_setup_2fa', None)
                session.pop('pre_2fa_user_id', None)
                login_user(user)
                session['user_role'] = user.role
                flash(f"2FA activee avec succes ! Bienvenue {user.first_name} !", 'success')
                return redirect_by_role(user.role)

            flash("Authentification a 2 facteurs activee avec succes !", 'success')
            return redirect(url_for('auth.profile'))
        else:
            log_action('2fa_setup_wrong_code', target_type='user',
                       target_id=user.id, target_name=user.email, user=user)
            flash("Code incorrect. Verifiez l'heure de votre telephone et reessayez.", 'danger')

    return render_template(
        'auth/setup_2fa.html',
        qr_base64=qr_base64,
        secret=user.totp_secret,
        forced_setup=session.get('must_setup_2fa', False)
    )


@auth_bp.route('/disable-2fa', methods=['POST'])
@login_required
def disable_2fa():
    """Desactiver la 2FA."""
    log_action('2fa_disabled', target_type='user',
               target_id=current_user.id, target_name=current_user.email)
    current_user.totp_enabled = False
    current_user.totp_secret = None
    db.session.commit()
    flash("Authentification a 2 facteurs desactivee.", 'info')
    return redirect(url_for('auth.profile'))


@auth_bp.route('/verify-2fa', methods=['GET', 'POST'])
@limiter.limit('10 per 5 minutes', methods=['POST'])
def verify_2fa():
    """Verification 2FA juste apres le login mot de passe."""
    user_id = session.get('pre_2fa_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    if not user or not user.totp_enabled:
        session.pop('pre_2fa_user_id', None)
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        totp = pyotp.TOTP(user.totp_secret)
        if totp.verify(code):
            session.pop('pre_2fa_user_id', None)
            login_user(user)
            session['user_role'] = user.role
            log_action('login_success_with_2fa', target_type='user',
                       target_id=user.id, target_name=user.email, user=user)
            flash(f'Bienvenue {user.first_name} !', 'success')
            return redirect_by_role(user.role)
        else:
            log_action('2fa_verify_failed', target_type='user',
                       target_id=user.id, target_name=user.email, user=user)
            flash("Code incorrect. Reessayez.", 'danger')

    return render_template('auth/verify_2fa.html', email=user.email)


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
