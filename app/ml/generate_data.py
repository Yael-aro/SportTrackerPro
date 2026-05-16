"""
Generateur de dataset synthetique pour la prediction de blessures.

CALIBRE sur les statistiques des donnees reelles Catapult Sports
(MAROC U16, RCA) - charge par ml_data/calibration_stats.json.

Modeles scientifiques :
- Gabbett 2016 : ACWR > 1.5 -> risque x4
- Carey 2018  : Wellness chronique bas -> +30% risque
- Hulin 2014  : Sommeil < 6h pendant 3 jours -> +50% risque
- Drew 2017   : Blessure recente (30j) -> risque x2

Ecrit ml_data/training_dataset.csv (~30 000 lignes).
"""

import json
import os
import numpy as np
import pandas as pd
from datetime import date, timedelta

np.random.seed(42)

CALIBRATION_PATH = 'ml_data/calibration_stats.json'
OUTPUT_PATH = 'ml_data/training_dataset.csv'


# =============================================================================
# CHARGER LA CALIBRATION DES DONNEES REELLES
# =============================================================================

def load_calibration():
    """Charge les stats issues de l'analyse des vraies donnees GPS."""
    if not os.path.exists(CALIBRATION_PATH):
        raise FileNotFoundError(
            f"{CALIBRATION_PATH} introuvable. Lancez d'abord:\n"
            "    python app/ml/analyze_real_data.py"
        )
    with open(CALIBRATION_PATH) as f:
        return json.load(f)


# =============================================================================
# PROFILS DE JOUEURS
# =============================================================================

def generate_player_profile(player_id):
    """Profil de joueur : age, poste, predisposition aux blessures."""
    return {
        'player_id': player_id,
        'age': int(np.random.randint(17, 35)),
        'position': np.random.choice(
            ['Gardien', 'Defenseur', 'Milieu', 'Attaquant'],
            p=[0.1, 0.35, 0.30, 0.25]
        ),
        'injury_prone': bool(np.random.random() < 0.20),
        'baseline_wellness': float(np.random.normal(7.5, 0.8)),
        'baseline_sleep': float(np.random.normal(7.5, 0.7)),
    }


# =============================================================================
# GENERATION D'UNE SEANCE CALIBREE SUR LES VRAIES DONNEES
# =============================================================================

def sample_from_stats(pos_stats, metric, fallback_mean=0, fallback_std=1):
    """Tire une valeur depuis une distribution N(mean, std) selon le poste."""
    if metric in pos_stats:
        mean = pos_stats[metric]['mean']
        std = pos_stats[metric]['std']
    else:
        mean = fallback_mean
        std = fallback_std
    value = np.random.normal(mean, std)
    return max(0, value)  # eviter les valeurs negatives


def generate_session_metrics(position, calibration, is_match=False, is_light=False):
    """Genere les metriques d'une seance pour un poste donne."""
    # Stats par poste depuis la calibration
    per_pos = calibration.get('per_position', {})
    pos_stats = per_pos.get(position, calibration.get('global', {}))

    # Multiplicateur match (+30%) ou seance legere (-50%)
    mult = 1.3 if is_match else (0.5 if is_light else 1.0)

    duration = sample_from_stats(pos_stats, 'duration_min', 75, 15) * mult
    total_distance = sample_from_stats(pos_stats, 'total_distance', 4500, 1500) * mult
    distance_sprint = sample_from_stats(pos_stats, 'distance_sprint', 100, 100) * mult
    nb_sprints = int(sample_from_stats(pos_stats, 'nb_sprints', 2, 3) * mult)
    vmax = sample_from_stats(pos_stats, 'vmax', 25, 3)
    nb_acc = int(sample_from_stats(pos_stats, 'nb_acc', 20, 10) * mult)
    nb_dec = int(sample_from_stats(pos_stats, 'nb_dec', 15, 8) * mult)
    high_speed = sample_from_stats(pos_stats, 'high_speed_running', 300, 250) * mult
    player_load = sample_from_stats(pos_stats, 'player_load', 500, 200) * mult
    m_per_min = sample_from_stats(pos_stats, 'meters_per_min', 75, 15)

    return {
        'duration_min': round(duration, 1),
        'total_distance': round(total_distance, 1),
        'distance_sprint': round(distance_sprint, 1),
        'nb_sprints': nb_sprints,
        'vmax': round(vmax, 2),
        'nb_acc': nb_acc,
        'nb_dec': nb_dec,
        'high_speed_running': round(high_speed, 1),
        'player_load': round(player_load, 1),
        'meters_per_min': round(m_per_min, 2),
    }


# =============================================================================
# MODELE DE RISQUE DE BLESSURE (litterature scientifique)
# =============================================================================

def compute_injury_probability(features, profile):
    """
    Probabilite de blessure dans les 7 prochains jours.
    Combine plusieurs facteurs de risque issus de la litterature.
    """
    base_risk = 0.015  # 1.5% par jour en football pro
    risk = base_risk

    # ACWR (Gabbett 2016)
    if features['acwr'] > 1.5:
        risk *= 8.0
    elif features['acwr'] > 1.3:
        risk *= 4.0
    elif features['acwr'] < 0.8:
        risk *= 1.8

    # Wellness (Carey 2018)
    if features['wellness_avg_7d'] < 5.0:
        risk *= 3.0
    elif features['wellness_avg_7d'] < 6.0:
        risk *= 1.8

    # Sommeil (Hulin 2014)
    if features['sleep_avg_7d'] < 6.0:
        risk *= 2.0
    elif features['sleep_avg_7d'] < 7.0:
        risk *= 1.5

    # Historique blessure (Drew 2017)
    if features['days_since_last_injury'] is not None and features['days_since_last_injury'] < 30:
        risk *= 2.5

    # Charge cumulee
    if features['acute_load'] > 3000:
        risk *= 1.4

    # Player Load cumule eleve
    if features['acute_player_load'] > 3500:
        risk *= 1.3

    # Age
    if profile['age'] > 30:
        risk *= 1.3
    elif profile['age'] < 20:
        risk *= 1.1

    # Predisposition
    if profile['injury_prone']:
        risk *= 1.5

    return min(risk, 0.95)


# =============================================================================
# GENERATION COMPLETE
# =============================================================================

def generate_dataset(n_players=50, n_days=600, output_path=OUTPUT_PATH):
    """
    Genere un dataset complet calibre sur les vraies donnees.

    Params:
        n_players : 50 joueurs synthetiques
        n_days    : 600 jours simules (~2 saisons)
        output_path : ml_data/training_dataset.csv
    """
    print("=" * 70)
    print("GENERATION DU DATASET SYNTHETIQUE CALIBRE")
    print("=" * 70)

    print("\n[1/3] Chargement de la calibration (vraies donnees)...")
    calibration = load_calibration()
    print(f"   -> Calibre sur {calibration['n_total_sessions']} seances reelles")
    print(f"   -> {calibration['n_players']} joueurs reels analyses")

    print(f"\n[2/3] Generation : {n_players} joueurs x {n_days} jours...")

    start_date = date(2024, 7, 1)
    all_rows = []

    for player_id in range(1, n_players + 1):
        profile = generate_player_profile(player_id)
        srpe_history = []
        player_load_history = []
        wellness_history = []
        sleep_history = []
        last_injury_date = None

        if player_id % 10 == 0:
            print(f"   Joueur {player_id}/{n_players}...")

        for day in range(n_days):
            current_date = start_date + timedelta(days=day)
            dow = current_date.weekday()
            is_competitive = current_date.month in [9, 10, 11, 12, 1, 2, 3, 4, 5]

            # Decider le type de seance
            if dow == 6:  # dimanche repos
                metrics = None
                rpe = 0
                is_match = False
            elif dow == 5 and is_competitive:  # samedi match
                metrics = generate_session_metrics(profile['position'], calibration, is_match=True)
                rpe = np.random.randint(8, 10)
                is_match = True
            elif dow < 5:  # entrainement semaine
                metrics = generate_session_metrics(profile['position'], calibration)
                rpe = np.random.randint(4, 8)
                is_match = False
            else:  # samedi sans match
                metrics = generate_session_metrics(profile['position'], calibration, is_light=True)
                rpe = np.random.randint(3, 6)
                is_match = False

            # Calcul des charges
            duration = metrics['duration_min'] if metrics else 0
            srpe = rpe * duration
            pl = metrics['player_load'] if metrics else 0

            # Wellness et sommeil
            wellness = max(1, min(10, profile['baseline_wellness'] + np.random.normal(0, 1.0)))
            sleep = max(3, min(11, profile['baseline_sleep'] + np.random.normal(0, 1.0)))
            if last_injury_date and (current_date - last_injury_date).days < 21:
                wellness -= 1.5
                sleep -= 0.5

            # Mise a jour historiques
            srpe_history.append(srpe)
            player_load_history.append(pl)
            wellness_history.append(wellness)
            sleep_history.append(sleep)

            # On a besoin d'au moins 28 jours d'historique
            if day < 28:
                continue

            # Features dynamiques
            acute_load = sum(srpe_history[-7:])
            chronic_load = sum(srpe_history[-28:]) / 4
            acwr = acute_load / chronic_load if chronic_load > 0 else 1.0

            acute_pl = sum(player_load_history[-7:])
            chronic_pl = sum(player_load_history[-28:]) / 4
            acwr_pl = acute_pl / chronic_pl if chronic_pl > 0 else 1.0

            days_since_injury = (current_date - last_injury_date).days if last_injury_date else None

            row = {
                'player_id': player_id,
                'date': current_date.isoformat(),
                'age': profile['age'],
                'position': profile['position'],

                # Metriques GPS du jour (calibrees Catapult)
                'duration_min': metrics['duration_min'] if metrics else 0,
                'total_distance': metrics['total_distance'] if metrics else 0,
                'distance_sprint': metrics['distance_sprint'] if metrics else 0,
                'nb_sprints': metrics['nb_sprints'] if metrics else 0,
                'vmax': metrics['vmax'] if metrics else 0,
                'nb_acc': metrics['nb_acc'] if metrics else 0,
                'nb_dec': metrics['nb_dec'] if metrics else 0,
                'high_speed_running': metrics['high_speed_running'] if metrics else 0,
                'player_load': metrics['player_load'] if metrics else 0,
                'meters_per_min': metrics['meters_per_min'] if metrics else 0,

                # Charges
                'srpe_today': round(srpe, 1),
                'rpe_today': rpe,
                'acute_load': round(acute_load, 1),
                'chronic_load': round(chronic_load, 1),
                'acwr': round(acwr, 2),
                'acute_player_load': round(acute_pl, 1),
                'chronic_player_load': round(chronic_pl, 1),
                'acwr_player_load': round(acwr_pl, 2),

                # Wellness
                'wellness_today': round(wellness, 1),
                'wellness_avg_7d': round(np.mean(wellness_history[-7:]), 1),
                'wellness_avg_28d': round(np.mean(wellness_history[-28:]), 1),

                # Sommeil
                'sleep_today': round(sleep, 1),
                'sleep_avg_7d': round(np.mean(sleep_history[-7:]), 1),
                'sleep_avg_28d': round(np.mean(sleep_history[-28:]), 1),

                # Historique blessure
                'days_since_last_injury': days_since_injury,
                'had_injury_30d': 1 if days_since_injury is not None and days_since_injury < 30 else 0,
                'had_injury_90d': 1 if days_since_injury is not None and days_since_injury < 90 else 0,

                # Contexte
                'is_match_day': int(is_match),
            }

            # Risque de blessure
            proba = compute_injury_probability(row, profile)
            row['injury_probability_true'] = round(proba, 3)

            # Tirage : blessure dans les 7 prochains jours ?
            injured = 0
            if np.random.random() < proba * 1.2:
                injured = 1
                last_injury_date = current_date + timedelta(days=np.random.randint(0, 7))

            row['injured_within_7d'] = injured
            all_rows.append(row)

    print(f"\n[3/3] Sauvegarde...")
    df = pd.DataFrame(all_rows)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)

    # Resume
    print(f"\n{'=' * 70}")
    print("RESUME")
    print(f"{'=' * 70}")
    print(f"Fichier         : {output_path}")
    print(f"Lignes          : {len(df):,}")
    print(f"Joueurs         : {df['player_id'].nunique()}")
    print(f"Periode         : {df['date'].min()} -> {df['date'].max()}")
    print(f"Distance moy.   : {df['total_distance'].mean():.0f} m (calibrage Catapult)")
    print(f"Player Load moy.: {df['player_load'].mean():.0f} UA")
    print(f"Vmax moy.       : {df['vmax'].mean():.2f} km/h")
    print(f"ACWR moyen      : {df['acwr'].mean():.2f}")
    print(f"Blessures 7d    : {df['injured_within_7d'].sum()} ({df['injured_within_7d'].mean()*100:.1f}%)")
    print(f"\nDistribution par poste :")
    print(df['position'].value_counts().to_string())

    return df


if __name__ == '__main__':
    generate_dataset()
