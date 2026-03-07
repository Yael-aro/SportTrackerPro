"""
SportTracker Pro - Routes d'Authentification
=============================================
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, Player
from app.forms import LoginForm, RegisterForm

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion multi-rôles"""
    if current_user.is_authenticated:
        return redirect_by_role(current_user.role)
    
    form = LoginForm()
    
    if form.validate_on_submit():
        email = form.email.data.lower()
        password = form.password.data
        role = form.role.data
        
        # Mode joueur simplifié
        if role == 'player':
            # Chercher le joueur par email ou prénom.nom
            player = find_player_by_email(email)
            
            if player:
                # Créer ou récupérer le compte utilisateur lié
                user = User.query.filter_by(player_id=player.id).first()
                
                if not user:
                    # Créer automatiquement un compte joueur
                    user = User(
                        email=email,
                        first_name=player.first_name,
                        last_name=player.last_name,
                        role='player',
                        player_id=player.id
                    )
                    user.set_password('player123')  # Mot de passe par défaut
                    db.session.add(user)
                    db.session.commit()
                
                login_user(user)
                session['user_role'] = 'player'
                session['player_id'] = player.id
                
                flash(f'Bienvenue {player.first_name} ! ', 'success')
                return redirect(url_for('player_portal.dashboard'))
            else:
                flash('Joueur non trouvé. Utilisez prenom.nom@email.com', 'danger')
        
        else:
            # Connexion staff (coach, medical, admin, etc.)
            user = User.query.filter_by(email=email).first()
            
            if user and user.check_password(password):
                if user.is_active:
                    login_user(user)
                    session['user_role'] = user.role
                    
                    flash(f'Bienvenue {user.first_name} ! ', 'success')
                    return redirect_by_role(user.role)
                else:
                    flash('Votre compte est désactivé.', 'danger')
            else:
                flash('Email ou mot de passe incorrect.', 'danger')
    
    # Récupérer la liste des joueurs pour l'aide à la connexion
    players = Player.query.order_by(Player.last_name).all()
    
    return render_template('auth/login.html', form=form, players=players)


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
    """Profil de l'utilisateur"""
    return render_template('auth/profile.html')


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def find_player_by_email(email):
    """
    Trouve un joueur par son email.
    Supporte le format prenom.nom@domain.com
    """
    # D'abord chercher par email exact
    player = Player.query.filter_by(email=email).first()
    if player:
        return player
    
    # Sinon, parser prenom.nom
    try:
        local_part = email.split('@')[0]
        parts = local_part.split('.')
        
        if len(parts) >= 2:
            first_name = parts[0]
            last_name = parts[1]
            
            player = Player.query.filter(
                db.func.lower(Player.first_name) == first_name.lower(),
                db.func.lower(Player.last_name) == last_name.lower()
            ).first()
            
            return player
    except:
        pass
    
    return None


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
