"""
Tests des modeles SportTracker Pro :
- User : hash mot de passe, role
- Team : creation, relations
- Player : age, BMI, full_name
"""
from datetime import date, timedelta
from app.models import User, Team, Player


# =============================================================================
# TESTS USER
# =============================================================================

class TestUser:
    """Tests du modele User."""

    def test_user_creation(self, app, coach_user):
        assert coach_user.id is not None
        assert coach_user.email == 'coach@test.com'
        assert coach_user.role == 'coach'
        assert coach_user.is_active is True

    def test_password_is_hashed(self, app, coach_user):
        """Le mot de passe ne doit JAMAIS etre stocke en clair."""
        assert coach_user.password_hash is not None
        assert coach_user.password_hash != 'coach123'
        assert 'coach123' not in coach_user.password_hash

    def test_check_password_correct(self, app, coach_user):
        assert coach_user.check_password('coach123') is True

    def test_check_password_wrong(self, app, coach_user):
        assert coach_user.check_password('mauvais_mdp') is False
        assert coach_user.check_password('') is False
        assert coach_user.check_password('COACH123') is False

    def test_full_name(self, app, coach_user):
        assert coach_user.full_name == 'Coach Test'

    def test_admin_role(self, app, admin_user):
        assert admin_user.role == 'admin'

    def test_medical_role(self, app, medical_user):
        assert medical_user.role == 'medical'

    def test_player_user_linked(self, app, player_user, player):
        """Le User joueur doit etre lie au Player via player_id."""
        assert player_user.player_id == player.id


# =============================================================================
# TESTS TEAM
# =============================================================================

class TestTeam:
    """Tests du modele Team."""

    def test_team_creation(self, app, team):
        assert team.id is not None
        assert team.name == 'Test FC'
        assert team.category == 'Senior'

    def test_team_default_loads(self, app, team):
        assert team.target_weekly_load == 400
        assert team.max_weekly_load == 600

    def test_team_empty_at_start(self, app, team):
        assert team.player_count == 0

    def test_team_with_one_player(self, app, team, player):
        assert team.player_count == 1
        assert player in team.players.all()


# =============================================================================
# TESTS PLAYER
# =============================================================================

class TestPlayer:
    """Tests du modele Player."""

    def test_player_creation(self, app, player):
        assert player.id is not None
        assert player.first_name == 'Test'
        assert player.last_name == 'Player'
        assert player.position == 'Milieu'
        assert player.jersey_number == 10

    def test_player_full_name(self, app, player):
        assert player.full_name == 'Test Player'

    def test_player_belongs_to_team(self, app, player, team):
        assert player.team_id == team.id
        assert player.team.name == 'Test FC'

    def test_player_age(self, app, player):
        """Age calcule a partir de date_of_birth (2000-05-15)."""
        expected_age = date.today().year - 2000
        if (date.today().month, date.today().day) < (5, 15):
            expected_age -= 1
        assert player.age == expected_age

    def test_player_bmi(self, app, player):
        """BMI = poids / (taille_en_m)^2 = 73 / (1.78)^2 ~= 23.04."""
        expected_bmi = round(73.0 / (1.78 ** 2), 1)
        assert player.bmi == expected_bmi

    def test_player_default_status(self, app, player):
        assert player.status == 'Disponible'

    def test_player_height_weight(self, app, player):
        assert player.height == 178.0
        assert player.weight == 73.0
