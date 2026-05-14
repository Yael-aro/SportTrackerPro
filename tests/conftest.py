"""
Fixtures pytest partagees pour SportTracker Pro.
Adaptees aux modeles reels du projet.
"""
import pytest
from datetime import date, datetime, time, timedelta
from app import create_app, db
from app.models import (
    User, Team, Player, TrainingSession, TrainingResult
)


@pytest.fixture(scope='function')
def app():
    """Application Flask configuree pour les tests (BDD en memoire)."""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Client HTTP de test."""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """Runner CLI de test."""
    return app.test_cli_runner()


@pytest.fixture
def admin_user(app):
    user = User(
        email='admin@test.com',
        first_name='Admin',
        last_name='Test',
        role='admin',
        is_active=True
    )
    user.set_password('admin123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def coach_user(app):
    user = User(
        email='coach@test.com',
        first_name='Coach',
        last_name='Test',
        role='coach',
        is_active=True
    )
    user.set_password('coach123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def medical_user(app):
    user = User(
        email='medical@test.com',
        first_name='Doc',
        last_name='Test',
        role='medical',
        is_active=True
    )
    user.set_password('medical123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def team(app):
    team = Team(
        name='Test FC',
        category='Senior',
        target_weekly_load=400,
        max_weekly_load=600
    )
    db.session.add(team)
    db.session.commit()
    return team


@pytest.fixture
def player(app, team):
    player = Player(
        team_id=team.id,
        first_name='Test',
        last_name='Player',
        date_of_birth=date(2000, 5, 15),
        position='Milieu',
        height=178.0,
        weight=73.0,
        jersey_number=10,
        status='Disponible'
    )
    db.session.add(player)
    db.session.commit()
    return player


@pytest.fixture
def player_user(app, player):
    user = User(
        email='player@test.com',
        first_name='Test',
        last_name='Player',
        role='player',
        is_active=True,
        player_id=player.id
    )
    user.set_password('player123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def player_with_history(app, player):
    """Joueur avec 8 semaines de seances : training_load=540 (RPE 6 x 90 min)."""
    today = date.today()
    base_date = today - timedelta(days=56)
    for day_offset in range(0, 56, 2):
        session_date = base_date + timedelta(days=day_offset)
        session = TrainingSession(
            title=f'Seance jour {day_offset}',
            team_id=player.team_id,
            date=session_date,
            session_type='Entrainement',
            duration=90,
            target_load=540
        )
        db.session.add(session)
        db.session.flush()
        result = TrainingResult(
            session_id=session.id,
            player_id=player.id,
            rpe=6,
            training_load=540
        )
        db.session.add(result)
    db.session.commit()
    return player


def login(client, email, password):
    return client.post('/auth/login', data={
        'email': email,
        'password': password
    }, follow_redirects=True)


def logout(client):
    return client.get('/auth/logout', follow_redirects=True)
