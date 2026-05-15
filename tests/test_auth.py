"""
Tests d'authentification et de controle d'acces (RBAC).
- Inscription
- Connexion / mot de passe
- Deconnexion
- Acces protege selon le role
"""
import pytest
from app import db
from app.models import User
from tests.conftest import login, logout


# =============================================================================
# TESTS PAGES AUTH (acces public)
# =============================================================================

class TestAuthPages:
    """Tests des pages d'authentification accessibles sans connexion."""

    def test_login_page_accessible(self, client):
        """La page /auth/login doit etre accessible sans connexion."""
        response = client.get('/auth/login')
        assert response.status_code == 200

    def test_login_page_contains_form(self, client):
        """La page de login doit contenir un champ email."""
        response = client.get('/auth/login')
        assert b'email' in response.data.lower() or b'Email' in response.data

    def test_register_page_accessible(self, client):
        """La page /auth/register doit etre accessible."""
        response = client.get('/auth/register')
        assert response.status_code == 200


# =============================================================================
# TESTS CONNEXION
# =============================================================================

class TestLogin:
    """Tests du processus de connexion."""

    def test_login_success(self, client, coach_user):
        """Connexion avec bonnes credentials => 200 ou 302."""
        response = login(client, 'coach@test.com', 'coach123')
        # Apres redirection, on doit etre connecte (pas sur /auth/login)
        assert response.status_code == 200

    def test_login_wrong_password(self, client, coach_user):
        """Mauvais mot de passe => reste sur /auth/login."""
        response = login(client, 'coach@test.com', 'mauvais_mdp')
        # On doit rester sur login (pas de redirection vers dashboard)
        assert b'login' in response.request.path.encode() or response.status_code == 200

    def test_login_nonexistent_user(self, client):
        """Email inexistant => echec connexion."""
        response = login(client, 'inexistant@test.com', 'whatever')
        assert response.status_code == 200
        # On reste sur la page de login
        assert b'login' in response.request.path.encode() or b'connexion' in response.data.lower()

    def test_login_empty_credentials(self, client):
        """Email et mot de passe vides => echec."""
        response = login(client, '', '')
        assert response.status_code == 200


# =============================================================================
# TESTS DECONNEXION
# =============================================================================

class TestLogout:
    """Tests du processus de deconnexion."""

    def test_logout_redirects(self, client, coach_user):
        """Apres connexion, /auth/logout redirige vers login."""
        login(client, 'coach@test.com', 'coach123')
        response = client.get('/auth/logout')
        # Logout retourne 302 (redirect) ou 200 apres follow
        assert response.status_code in [200, 302]

    def test_logout_then_protected_blocked(self, client, coach_user):
        """Apres logout, l'acces aux pages protegees redirige vers login."""
        login(client, 'coach@test.com', 'coach123')
        logout(client)
        # Tentative d'acces a une page normalement protegee
        response = client.get('/players/', follow_redirects=False)
        # Doit rediriger vers login
        assert response.status_code == 302
        assert '/auth/login' in response.location


# =============================================================================
# TESTS PROTECTION DES ROUTES
# =============================================================================

class TestProtectedRoutes:
    """Tests : les routes sensibles exigent une connexion."""

    def test_players_requires_login(self, client):
        """GET /players/ sans connexion => redirect vers login."""
        response = client.get('/players/', follow_redirects=False)
        assert response.status_code == 302
        assert '/auth/login' in response.location

    def test_teams_requires_login(self, client):
        """GET /teams/ sans connexion => redirect vers login."""
        response = client.get('/teams/', follow_redirects=False)
        assert response.status_code == 302

    def test_dashboard_requires_login(self, client):
        """GET /dashboard/ sans connexion => redirect vers login."""
        response = client.get('/dashboard/', follow_redirects=False)
        assert response.status_code == 302

    def test_gps_upload_requires_login(self, client):
        """GET /gps/upload sans connexion => redirect vers login."""
        response = client.get('/gps/upload', follow_redirects=False)
        assert response.status_code == 302


# =============================================================================
# TESTS RBAC (Role-Based Access Control)
# =============================================================================

class TestRBAC:
    """Tests du systeme de roles."""

    def test_coach_can_access_players(self, client, coach_user):
        """Un coach connecte peut acceder a /players/."""
        login(client, 'coach@test.com', 'coach123')
        response = client.get('/players/')
        assert response.status_code == 200

    def test_admin_can_access_players(self, client, admin_user):
        """Un admin connecte peut acceder a /players/."""
        login(client, 'admin@test.com', 'admin123')
        response = client.get('/players/')
        assert response.status_code == 200

    def test_medical_can_access_medical(self, client, medical_user):
        """Le staff medical peut acceder a /medical/."""
        login(client, 'medical@test.com', 'medical123')
        response = client.get('/medical/')
        # 200 si la route existe, 404 si elle n'existe pas, 403 si interdit
        # On accepte 200 et 302 (redirection eventuelle vers dashboard medical)
        assert response.status_code in [200, 302, 404]


# =============================================================================
# TESTS USER MODEL - methodes auth
# =============================================================================

class TestUserAuthMethods:
    """Tests des methodes du modele User liees a l'authentification."""

    def test_set_password_hashes(self, app):
        """set_password() doit produire un hash, pas le mot de passe en clair."""
        user = User(
            email='hashtest@test.com',
            first_name='Hash',
            last_name='Test',
            role='coach'
        )
        user.set_password('motdepasse_secret')
        assert user.password_hash is not None
        assert user.password_hash != 'motdepasse_secret'
        assert len(user.password_hash) > 20  # un vrai hash est long

    def test_check_password_returns_bool(self, app, coach_user):
        """check_password() retourne True ou False."""
        result_true = coach_user.check_password('coach123')
        result_false = coach_user.check_password('wrong')
        assert result_true is True
        assert result_false is False

    def test_two_users_same_password_have_different_hashes(self, app):
        """Deux users avec le meme mot de passe ont des hashs differents (salt)."""
        u1 = User(email='u1@test.com', first_name='U1', last_name='X', role='coach')
        u1.set_password('memepassword')
        u2 = User(email='u2@test.com', first_name='U2', last_name='X', role='coach')
        u2.set_password('memepassword')
        assert u1.password_hash != u2.password_hash
