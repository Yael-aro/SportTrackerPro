"""
Seed des donnees reelles : Raja Club Athletic avec les vrais joueurs.

Contexte : Le Raja Casablanca n'a pas de gilets GPS dans sa formation.
Les donnees GPS sont recueillies lors des stages de selection MAROC U16
organises par la FRMF (Federation Royale Marocaine de Football).
Le projet RajaTracker permet au Raja d'exploiter ces donnees pour le
suivi de ses joueurs.

Usage :
    python -m app.seed_real_data
"""

from datetime import date

from app import create_app, db
from app.models import Team, Player


TEAMS = [
    {
        'name': 'Raja Club Athletic',
        'description': 'Centre de formation du Raja Casablanca. Donnees GPS recueillies lors des stages MAROC U16 (FRMF).',
        'category': 'Formation',
    },
]

PLAYERS = [
    {
        'first_name': 'Ismail',
        'last_name': 'CHBILI',
        'position': 'Attaquant',
        'team_name': 'Raja Club Athletic',
        'date_of_birth': date(2009, 1, 1),
        'dominant_foot': 'Droit',
        'jersey_number': 9,
        'status': 'Disponible',
    },
    {
        'first_name': 'Mehdi',
        'last_name': 'AMEHMOUL',
        'position': 'Defenseur central',
        'team_name': 'Raja Club Athletic',
        'date_of_birth': date(2009, 6, 15),
        'dominant_foot': 'Droit',
        'jersey_number': 4,
        'status': 'Disponible',
    },
    {
        'first_name': 'Adam Mohamed',
        'last_name': 'ABID',
        'position': 'Defenseur lateral',
        'team_name': 'Raja Club Athletic',
        'date_of_birth': date(2009, 3, 22),
        'dominant_foot': 'Droit',
        'jersey_number': 2,
        'status': 'Disponible',
    },
    {
        'first_name': 'Ammar',
        'last_name': 'BOULKAMH',
        'position': 'Milieu',
        'team_name': 'Raja Club Athletic',
        'date_of_birth': date(2008, 9, 10),
        'dominant_foot': 'Droit',
        'jersey_number': 8,
        'status': 'Disponible',
    },
    {
        'first_name': 'Yahya',
        'last_name': 'IGUIZ',
        'position': 'Attaquant',
        'team_name': 'Raja Club Athletic',
        'date_of_birth': date(2008, 5, 18),
        'dominant_foot': 'Gauche',
        'jersey_number': 10,
        'status': 'Disponible',
    },
]


def seed():
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("SEED DES DONNEES REELLES - RAJA CLUB ATHLETIC")
        print("=" * 60)

        # 1. Equipes
        print("\n[1/2] Creation des equipes...")
        teams_by_name = {}
        for t in TEAMS:
            existing = Team.query.filter_by(name=t['name']).first()
            if existing:
                print(f"   - {t['name']} (deja existe, id={existing.id})")
                teams_by_name[t['name']] = existing
            else:
                team = Team(
                    name=t['name'],
                    description=t['description'],
                    category=t['category'],
                    target_weekly_load=400,
                    max_weekly_load=600,
                )
                db.session.add(team)
                db.session.flush()
                print(f"   + {t['name']} (cree, id={team.id})")
                teams_by_name[t['name']] = team

        # 2. Joueurs
        print(f"\n[2/2] Creation des joueurs...")
        for p in PLAYERS:
            team = teams_by_name.get(p['team_name'])
            if not team:
                print(f"   ! Equipe '{p['team_name']}' introuvable, joueur ignore")
                continue

            existing = Player.query.filter_by(
                first_name=p['first_name'],
                last_name=p['last_name'],
            ).first()
            if existing:
                print(f"   - {p['first_name']} {p['last_name']} (deja existe, id={existing.id})")
                continue

            player = Player(
                first_name=p['first_name'],
                last_name=p['last_name'],
                date_of_birth=p['date_of_birth'],
                position=p['position'],
                jersey_number=p['jersey_number'],
                dominant_foot=p['dominant_foot'],
                status=p['status'],
                team_id=team.id,
            )
            db.session.add(player)
            print(f"   + {p['first_name']} {p['last_name']} -> {p['team_name']} ({p['position']})")

        db.session.commit()

        print("\n" + "=" * 60)
        print("RESUME")
        print("=" * 60)
        print(f"Total equipes : {Team.query.count()}")
        print(f"Total joueurs : {Player.query.count()}")
        print("\nVous pouvez maintenant importer MAROC_RCA_All_Data.xlsx via /gps/upload")


if __name__ == '__main__':
    seed()
