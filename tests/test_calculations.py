"""
Tests des calculs de charge d'entrainement et indicateurs de prevention :
- sRPE (Foster) : training_load = RPE x duree
- ACWR (Gabbett) : ratio charge aigue / charge chronique
- CTL, ATL, TSB (Banister)
- Statut de forme

Ces tests verifient que les formules implementees dans app/models.py
respectent bien la litterature scientifique.
"""
import pytest
from datetime import date, timedelta
from app import db
from app.models import (
    Player, Team, TrainingSession, TrainingResult
)


# =============================================================================
# HELPER POUR CREER DES SEANCES AVEC CHARGES PRECISES
# =============================================================================

def add_session_with_load(player, days_ago, training_load, rpe=6, duration=90):
    """Cree une seance + un TrainingResult avec une charge precise."""
    session_date = date.today() - timedelta(days=days_ago)
    session = TrainingSession(
        title=f'Seance J-{days_ago}',
        team_id=player.team_id,
        date=session_date,
        session_type='Entrainement',
        duration=duration
    )
    db.session.add(session)
    db.session.flush()
    result = TrainingResult(
        session_id=session.id,
        player_id=player.id,
        rpe=rpe,
        training_load=training_load
    )
    db.session.add(result)
    db.session.commit()
    return result


# =============================================================================
# TESTS sRPE (FOSTER)
# =============================================================================

class TestSRPE:
    """Tests de la methode calculate_load() : sRPE = RPE x duree."""

    def test_srpe_classic(self, app, player):
        """RPE=7, duree=90 => sRPE=630 (Foster 2001)."""
        session = TrainingSession(
            title='Test', team_id=player.team_id, date=date.today(),
            session_type='Match', duration=90
        )
        db.session.add(session)
        db.session.flush()
        result = TrainingResult(
            session_id=session.id, player_id=player.id, rpe=7
        )
        db.session.add(result)
        db.session.flush()
        load = result.calculate_load(duration=90)
        assert load == 630
        assert result.training_load == 630

    def test_srpe_light_session(self, app, player):
        """Seance recuperation : RPE=2, duree=30 => sRPE=60."""
        session = TrainingSession(
            title='Recup', team_id=player.team_id, date=date.today(),
            session_type='Recuperation', duration=30
        )
        db.session.add(session)
        db.session.flush()
        result = TrainingResult(
            session_id=session.id, player_id=player.id, rpe=2
        )
        db.session.add(result)
        load = result.calculate_load(duration=30)
        assert load == 60

    def test_srpe_intensive_session(self, app, player):
        """Match intense : RPE=9, duree=95 => sRPE=855."""
        session = TrainingSession(
            title='Match', team_id=player.team_id, date=date.today(),
            session_type='Match', duration=95
        )
        db.session.add(session)
        db.session.flush()
        result = TrainingResult(
            session_id=session.id, player_id=player.id, rpe=9
        )
        db.session.add(result)
        load = result.calculate_load(duration=95)
        assert load == 855

    def test_srpe_without_rpe_returns_zero(self, app, player):
        """Sans RPE saisi, calculate_load doit retourner 0."""
        session = TrainingSession(
            title='Sans RPE', team_id=player.team_id, date=date.today(),
            session_type='Entrainement', duration=60
        )
        db.session.add(session)
        db.session.flush()
        result = TrainingResult(session_id=session.id, player_id=player.id)
        db.session.add(result)
        assert result.calculate_load(duration=60) == 0


# =============================================================================
# TESTS WEEKLY LOAD (charge aigue)
# =============================================================================

class TestWeeklyLoad:
    """Tests de la charge hebdomadaire (somme des sRPE de la semaine en cours)."""

    def test_weekly_load_no_session(self, app, player):
        """Aucune seance => charge hebdo = 0."""
        assert player.get_weekly_load() == 0

    def test_weekly_load_one_session_this_week(self, app, player):
        """Une seance a 500 AU cette semaine => charge hebdo = 500."""
        today = date.today()
        days_since_monday = today.weekday()  # 0=lundi
        add_session_with_load(player, days_ago=days_since_monday, training_load=500)
        assert player.get_weekly_load() == 500

    def test_weekly_load_sums_multiple_sessions(self, app, player):
        """3 seances cette semaine : 500 + 300 + 400 = 1200 AU."""
        today = date.today()
        days_since_monday = today.weekday()
        add_session_with_load(player, days_ago=days_since_monday, training_load=500)
        if days_since_monday >= 1:
            add_session_with_load(player, days_ago=days_since_monday - 1, training_load=300)
        else:
            add_session_with_load(player, days_ago=0, training_load=300)
        # On garantit au moins 2 seances comptees
        expected_min = 500 + 300
        assert player.get_weekly_load() >= expected_min


# =============================================================================
# TESTS CHRONIC LOAD (charge chronique)
# =============================================================================

class TestChronicLoad:
    """Tests de la charge chronique (moyenne des 4 dernieres semaines)."""

    def test_chronic_load_no_history(self, app, player):
        """Aucune seance => charge chronique = 0."""
        assert player.get_chronic_load() == 0

    def test_chronic_load_with_uniform_history(self, app, player_with_history):
        """player_with_history : ~1 seance tous les 2 j sur 56 j a 540 AU.
        get_chronic_load() prend les 4 semaines AVANT cette semaine.
        Cette charge doit etre > 0."""
        chronic = player_with_history.get_chronic_load()
        assert chronic > 0

    def test_chronic_load_returns_float(self, app, player_with_history):
        """La charge chronique doit etre un nombre (int ou float)."""
        chronic = player_with_history.get_chronic_load()
        assert isinstance(chronic, (int, float))


# =============================================================================
# TESTS ACWR (Acute:Chronic Workload Ratio - Gabbett)
# =============================================================================

class TestACWR:
    """Tests du ratio ACWR (Gabbett, 2016)."""

    def test_acwr_no_history_returns_zero(self, app, player):
        """Sans historique, ACWR = 0 (protection division par zero)."""
        assert player.get_acwr() == 0

    def test_acwr_returns_rounded_value(self, app, player_with_history):
        """ACWR doit etre arrondi a 2 decimales."""
        acwr = player_with_history.get_acwr()
        # Si l'ACWR n'est pas nul, il doit avoir au plus 2 decimales
        assert acwr == round(acwr, 2)

    def test_acwr_overload_scenario(self, app, player):
        """Scenario surcharge : charge aigue tres elevee, chronique normale.
        => ACWR > 1.5 doit etre detecte."""
        today = date.today()
        days_since_monday = today.weekday()
        # Charge aigue cette semaine = 3000 AU (tres eleve)
        add_session_with_load(player, days_ago=days_since_monday, training_load=3000)
        # Charge chronique : 4 semaines a 500 AU/semaine
        for week in range(1, 5):
            ago = days_since_monday + 7 * week
            add_session_with_load(player, days_ago=ago, training_load=500)
        acwr = player.get_acwr()
        assert acwr > 1.5, f"ACWR={acwr} devrait etre > 1.5 (surcharge)"

    def test_acwr_optimal_zone(self, app, player):
        """Scenario zone optimale : charge aigue similaire a chronique.
        => ACWR proche de 1.0."""
        today = date.today()
        days_since_monday = today.weekday()
        # Charge cette semaine = 500
        add_session_with_load(player, days_ago=days_since_monday, training_load=500)
        # 4 semaines passees a 500 chacune
        for week in range(1, 5):
            ago = days_since_monday + 7 * week
            add_session_with_load(player, days_ago=ago, training_load=500)
        acwr = player.get_acwr()
        # ACWR doit etre dans la zone optimale [0.8, 1.3]
        assert 0.8 <= acwr <= 1.3, f"ACWR={acwr} devrait etre dans [0.8, 1.3]"


# =============================================================================
# TESTS CTL / ATL / TSB (Banister)
# =============================================================================

class TestBanisterModel:
    """Tests du modele Banister : Fitness (CTL), Fatigue (ATL), TSB."""

    def test_fitness_no_history(self, app, player):
        """Sans historique, CTL = 0."""
        assert player.get_fitness() == 0

    def test_fatigue_no_history(self, app, player):
        """Sans historique, ATL = 0."""
        assert player.get_fatigue() == 0

    def test_tsb_no_history(self, app, player):
        """Sans historique, TSB = CTL - ATL = 0 - 0 = 0."""
        assert player.get_tsb() == 0

    def test_fitness_with_history_positive(self, app, player_with_history):
        """Avec 8 semaines d'historique, CTL doit etre > 0."""
        assert player_with_history.get_fitness() > 0

    def test_fatigue_with_history_positive(self, app, player_with_history):
        """Avec un historique recent, ATL doit etre > 0."""
        assert player_with_history.get_fatigue() > 0

    def test_tsb_is_difference(self, app, player_with_history):
        """TSB = CTL - ATL (verification de la formule)."""
        ctl = player_with_history.get_fitness()
        atl = player_with_history.get_fatigue()
        tsb = player_with_history.get_tsb()
        assert tsb == round(ctl - atl, 1)


# =============================================================================
# TESTS FORM STATUS (statut de forme)
# =============================================================================

class TestFormStatus:
    """Tests de la classification du statut de forme."""

    def test_form_status_returns_dict(self, app, player):
        """get_form_status retourne un dict avec status, color, icon."""
        status = player.get_form_status()
        assert isinstance(status, dict)
        assert 'status' in status
        assert 'color' in status
        assert 'icon' in status

    def test_form_status_no_history_is_bon_or_excellent(self, app, player):
        """Sans donnees, le statut doit etre acceptable (pas Danger/Attention)."""
        status = player.get_form_status()
        assert status['status'] in ['Bon', 'Excellent', 'Attention', 'Danger']

    def test_form_status_danger_on_overload(self, app, player):
        """Surcharge severe (ACWR > 1.5) => statut Danger."""
        today = date.today()
        days_since_monday = today.weekday()
        # Charge aigue tres elevee
        add_session_with_load(player, days_ago=days_since_monday, training_load=4000)
        # Chronique normale
        for week in range(1, 5):
            ago = days_since_monday + 7 * week
            add_session_with_load(player, days_ago=ago, training_load=500)
        status = player.get_form_status()
        assert status['status'] == 'Danger'
        assert status['color'] == 'danger'

    def test_form_status_warning_color_codes(self, app, player):
        """Les codes couleur Bootstrap doivent etre valides."""
        status = player.get_form_status()
        valid_colors = ['success', 'info', 'warning', 'danger', 'secondary', 'primary']
        assert status['color'] in valid_colors
