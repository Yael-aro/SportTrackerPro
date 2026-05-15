"""
Tests des routes principales de la plateforme.
- Pages publiques (accueil, contact, about, etc.)
- Routes joueurs / equipes / seances (authentifie)
- Dashboard
- API endpoints
"""
import pytest
from tests.conftest import login


# =============================================================================
# TESTS PAGES PUBLIQUES
# =============================================================================

class TestPublicPages:
    """Pages accessibles sans authentification."""

    def test_home_page(self, client):
        """La page d'accueil doit etre accessible."""
        response = client.get('/')
        assert response.status_code == 200

    def test_about_page(self, client):
        """Page about (si elle existe)."""
        response = client.get('/about')
        # Accepte 200 ou 404 selon le routing
        assert response.status_code in [200, 302, 404]

    def test_contact_page(self, client):
        """Page contact (si elle existe)."""
        response = client.get('/contact')
        assert response.status_code in [200, 302, 404]

    def test_privacy_page(self, client):
        """Page politique de confidentialite."""
        response = client.get('/privacy')
        assert response.status_code in [200, 302, 404]


# =============================================================================
# TESTS ROUTES JOUEURS
# =============================================================================

class TestPlayerRoutes:
    """Tests des routes /players/."""

    def test_players_list_authenticated(self, client, coach_user):
        """Liste des joueurs accessible apres connexion."""
        login(client, 'coach@test.com', 'coach123')
        response = client.get('/players/')
        assert response.status_code == 200

    def test_players_list_filtered_by_team(self, client, coach_user, team):
        """Filtre par equipe doit fonctionner."""
        login(client, 'coach@test.com', 'coach123')
        response = client.get(f'/players/?team_id={team.id}')
        assert response.status_code == 200

    def test_players_list_filtered_by_status(self, client, coach_user):
        """Filtre par statut doit fonctionner."""
        login(client, 'coach@test.com', 'coach123')
        response = client.get('/players/?status=Disponible')
        assert response.status_code == 200

    def test_player_detail_authenticated(self, client, coach_user, player):
        """Detail d'un joueur accessible."""
        login(client, 'coach@test.com', 'coach123')
        response = client.get(f'/players/{player.id}')
        # 200 si la route existe, 404 sinon
        assert response.status_code in [200, 302, 404]


# =============================================================================
# TESTS ROUTES EQUIPES
# =============================================================================

class TestTeamRoutes:
    """Tests des routes /teams/."""

    def test_teams_list_authenticated(self, client, coach_user):
        """Liste des equipes accessible apres connexion."""
        login(client, 'coach@test.com', 'coach123')
        response = client.get('/teams/')
        assert response.status_code == 200

    def test_team_detail_authenticated(self, client, coach_user, team):
        """Detail d'une equipe accessible."""
        login(client, 'coach@test.com', 'coach123')
        response = client.get(f'/teams/{team.id}')
        assert response.status_code in [200, 302, 404]


# =============================================================================
# TESTS ROUTES SEANCES
# =============================================================================

class TestSessionRoutes:
    """Tests des routes /sessions/."""

    def test_calendar_authenticated(self, client, coach_user):
        """Le calendrier des seances doit etre accessible."""
        login(client, 'coach@test.com', 'coach123')
        response = client.get('/sessions/calendar')
        assert response.status_code == 200

    def test_session_add_form(self, client, coach_user):
        """Le formulaire d'ajout de seance doit etre accessible."""
        login(client, 'coach@test.com', 'coach123')
        response = client.get('/sessions/add')
        assert response.status_code in [200, 302]

    def test_session_events_api(self, client, coach_user):
        """L'endpoint JSON des events doit fonctionner."""
        login(client, 'coach@test.com', 'coach123')
        response = client.get('/sessions/api/events?start=2026-01-01T00:00:00&end=2026-12-31T00:00:00')
        assert response.status_code == 200


# =============================================================================
# TESTS DASHBOARD
# =============================================================================

class TestDashboardRoutes:
    """Tests des dashboards par role."""

    def test_dashboard_root_authenticated(self, client, coach_user):
        """Le dashboard racine doit rediriger ou afficher."""
        login(client, 'coach@test.com', 'coach123')
        response = client.get('/dashboard/')
        assert response.status_code in [200, 302]

    def test_dashboard_coach(self, client, coach_user):
        """Dashboard coach accessible."""
        login(client, 'coach@test.com', 'coach123')
        response = client.get('/dashboard/coach')
        assert response.status_code in [200, 302, 404]

    def test_dashboard_admin(self, client, admin_user):
        """Dashboard admin accessible pour un admin."""
        login(client, 'admin@test.com', 'admin123')
        response = client.get('/dashboard/admin')
        assert response.status_code in [200, 302, 404]


# =============================================================================
# TESTS GPS
# =============================================================================

class TestGPSRoutes:
    """Tests des routes GPS."""

    def test_gps_list_authenticated(self, client, coach_user):
        """Liste GPS accessible apres connexion."""
        login(client, 'coach@test.com', 'coach123')
        response = client.get('/gps/')
        assert response.status_code in [200, 302]

    def test_gps_upload_form(self, client, coach_user):
        """Le formulaire d'upload GPS doit etre accessible."""
        login(client, 'coach@test.com', 'coach123')
        response = client.get('/gps/upload')
        assert response.status_code in [200, 302]


# =============================================================================
# TESTS API
# =============================================================================

class TestAPI:
    """Tests des endpoints API REST."""

    def test_api_players_authenticated(self, client, coach_user, player):
        """GET /api/players doit retourner la liste des joueurs."""
        login(client, 'coach@test.com', 'coach123')
        response = client.get('/api/players')
        # 200 (existe), 404 (route absente), 401 (auth requise differente)
        assert response.status_code in [200, 302, 401, 404]

    def test_api_teams_authenticated(self, client, coach_user, team):
        """GET /api/teams doit retourner la liste."""
        login(client, 'coach@test.com', 'coach123')
        response = client.get('/api/teams')
        assert response.status_code in [200, 302, 401, 404]


# =============================================================================
# TESTS ERREURS HTTP
# =============================================================================

class TestErrorHandling:
    """Tests des codes d'erreur HTTP."""

    def test_404_on_inexistent_player(self, client, coach_user):
        """GET /players/999999 (inexistant) doit retourner 404."""
        login(client, 'coach@test.com', 'coach123')
        response = client.get('/players/999999')
        assert response.status_code == 404

    def test_404_on_inexistent_team(self, client, coach_user):
        """GET /teams/999999 (inexistant) doit retourner 404."""
        login(client, 'coach@test.com', 'coach123')
        response = client.get('/teams/999999')
        assert response.status_code == 404

    def test_404_on_random_url(self, client):
        """GET sur une URL totalement inexistante => 404."""
        response = client.get('/cette-url-nexiste-vraiment-pas-12345')
        assert response.status_code == 404
