"""
SportTracker Pro - Point d'entrée
=================================
Lancez l'application avec: python run.py
"""

import os
from app import create_app, db
from app.models import User, Team, Player, TrainingSession

# Créer l'application
app = create_app(os.environ.get('FLASK_CONFIG') or 'development')


@app.shell_context_processor
def make_shell_context():
    """Contexte pour flask shell"""
    return {
        'db': db,
        'User': User,
        'Team': Team,
        'Player': Player,
        'TrainingSession': TrainingSession
    }


@app.cli.command()
def init_db():
    """Initialiser la base de données avec des données de test"""
    from datetime import date, timedelta
    
    print("🔄 Création des tables...")
    db.create_all()
    
    # Vérifier si des données existent
    if Team.query.first():
        print("⚠️ Des données existent déjà. Utilisez 'flask reset-db' pour réinitialiser.")
        return
    
    print("📝 Ajout des données de test...")
    
    # Créer un admin
    admin = User(
        email='admin@sporttracker.com',
        first_name='Admin',
        last_name='System',
        role='admin'
    )
    admin.set_password('admin123')
    db.session.add(admin)
    
    # Créer un coach
    coach = User(
        email='coach@sporttracker.com',
        first_name='Mohamed',
        last_name='Bencherif',
        role='coach'
    )
    coach.set_password('coach123')
    db.session.add(coach)
    
    # Créer les équipes
    teams = [
        Team(name='Seniors A', category='Seniors', description='Équipe première'),
        Team(name='U19', category='U19', description='Moins de 19 ans'),
        Team(name='U17', category='U17', description='Moins de 17 ans')
    ]
    for team in teams:
        db.session.add(team)
    
    db.session.commit()
    
    # Créer les joueurs
    players_data = [
        # Seniors A
        ('Youssef', 'El Amrani', '1998-03-15', 'Gardien', 1),
        ('Karim', 'Benali', '1997-07-22', 'Défenseur', 1),
        ('Omar', 'Tazi', '1999-01-08', 'Défenseur', 1),
        ('Mehdi', 'Alaoui', '1998-11-30', 'Milieu', 1),
        ('Amine', 'Rachidi', '2000-05-14', 'Milieu', 1),
        ('Hamza', 'Idrissi', '1999-09-03', 'Attaquant', 1),
        ('Said', 'Moussaoui', '1998-12-20', 'Attaquant', 1),
        # U19
        ('Ayoub', 'Mansouri', '2006-02-20', 'Gardien', 2),
        ('Bilal', 'Chakir', '2006-08-11', 'Défenseur', 2),
        ('Reda', 'Fikri', '2007-04-05', 'Milieu', 2),
        ('Soufiane', 'Berrada', '2006-12-18', 'Attaquant', 2),
        # U17
        ('Adam', 'Ouazzani', '2008-06-25', 'Gardien', 3),
        ('Zakaria', 'Lamrani', '2009-03-10', 'Défenseur', 3),
        ('Othmane', 'Hajji', '2008-10-07', 'Milieu', 3),
    ]
    
    for first, last, dob, pos, team_id in players_data:
        player = Player(
            first_name=first,
            last_name=last,
            date_of_birth=date.fromisoformat(dob),
            position=pos,
            team_id=team_id,
            status='Disponible'
        )
        db.session.add(player)
    
    db.session.commit()
    
    # Créer quelques séances
    today = date.today()
    sessions_data = [
        ('Préparation physique', 'Cardio', today - timedelta(days=5), 90, 1, True),
        ('Travail technique', 'Technique', today - timedelta(days=3), 75, 1, True),
        ('Tactique offensive', 'Tactique', today - timedelta(days=1), 60, 1, True),
        ('Entraînement cardio', 'Cardio', today + timedelta(days=1), 90, 1, False),
        ('Match amical', 'Match amical', today + timedelta(days=3), 90, 2, False),
    ]
    
    for title, stype, sdate, duration, team_id, completed in sessions_data:
        session = TrainingSession(
            title=title,
            session_type=stype,
            date=sdate,
            duration=duration,
            team_id=team_id,
            is_completed=completed
        )
        db.session.add(session)
    
    db.session.commit()
    
    print("✅ Base de données initialisée avec succès !")
    print("\n📧 Comptes de test :")
    print("   Admin: admin@sporttracker.com / admin123")
    print("   Coach: coach@sporttracker.com / coach123")
    print("   Joueur: youssef.elamrani@sporttracker.com (sans mot de passe)")


@app.cli.command()
def reset_db():
    """Réinitialiser la base de données"""
    if input("⚠️ Supprimer toutes les données ? (oui/non) : ").lower() == 'oui':
        db.drop_all()
        print("🗑️ Tables supprimées.")
        db.create_all()
        print("✅ Tables recréées. Lancez 'flask init-db' pour ajouter des données.")
    else:
        print("❌ Annulé.")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
