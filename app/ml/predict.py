"""
Service de prediction de blessure.

Charge le modele entraine et fournit une API simple pour predire
le risque de blessure dans les 7 prochains jours pour un joueur.
"""

import os
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

MODEL_PATH = 'ml_models/injury_predictor.joblib'

# Cache du modele (charge une seule fois)
_model_cache = None


def load_model():
    """Charge le modele depuis le disque (avec cache en memoire)."""
    global _model_cache
    if _model_cache is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Modele introuvable : {MODEL_PATH}. "
                f"Entrainez d'abord avec : python app/ml/train_model.py"
            )
        _model_cache = joblib.load(MODEL_PATH)
    return _model_cache


def engineer_features_for_prediction(row_dict):
    """
    Genere les features derivees pour une prediction unique.
    Doit etre coherent avec train_model.engineer_features().
    """
    r = row_dict.copy()

    # Zones ACWR
    acwr = r.get('acwr', 1.0)
    r['acwr_danger'] = int(acwr > 1.5)
    r['acwr_warning'] = int(1.3 < acwr <= 1.5)
    r['acwr_undertraining'] = int(acwr < 0.8)
    r['acwr_optimal'] = int(0.8 <= acwr <= 1.3)

    # Zones wellness
    w7 = r.get('wellness_avg_7d', 7.0)
    r['wellness_low'] = int(w7 < 5.0)
    r['wellness_medium'] = int(5.0 <= w7 < 6.0)

    # Zones sommeil
    s7 = r.get('sleep_avg_7d', 7.5)
    r['sleep_insufficient'] = int(s7 < 6.0)
    r['sleep_suboptimal'] = int(6.0 <= s7 < 7.0)

    # Tendances
    r['wellness_trend'] = w7 - r.get('wellness_avg_28d', w7)
    r['sleep_trend'] = s7 - r.get('sleep_avg_28d', s7)

    # Zones de charge
    r['acute_load_high'] = int(r.get('acute_load', 0) > 3000)
    r['acute_pl_high'] = int(r.get('acute_player_load', 0) > 3500)

    # Interactions
    r['double_risk_wellness_acwr'] = int(w7 < 6.0 and acwr > 1.3)
    r['double_risk_sleep_injury'] = int(s7 < 6.5 and r.get('had_injury_30d', 0) == 1)
    r['triple_risk'] = int(w7 < 6.0 and acwr > 1.3 and s7 < 7.0)

    # Stress score
    r['stress_score'] = (
        r['acwr_danger'] * 3 +
        r['acwr_warning'] * 2 +
        r['wellness_low'] * 2 +
        r['sleep_insufficient'] * 2 +
        r.get('had_injury_30d', 0) * 2 +
        r['acute_load_high'] * 1
    )

    # Ratios
    duration = r.get('duration_min', 0)
    r['sprint_per_min'] = r.get('distance_sprint', 0) / (duration + 1)
    r['load_per_min'] = r.get('player_load', 0) / (duration + 1)

    # Age
    age = r.get('age', 25)
    r['age_young'] = int(age < 20)
    r['age_old'] = int(age > 30)

    # Historique blessure
    dsi = r.get('days_since_last_injury')
    r['days_since_injury_filled'] = dsi if dsi is not None else 365
    r['recent_injury_log'] = float(np.log1p(365 - min(max(r['days_since_injury_filled'], 0), 365)))

    return r


def predict_risk(player_features):
    """
    Predit le risque de blessure pour un joueur.

    Args:
        player_features (dict): dict avec au moins les cles suivantes:
            age, position, duration_min, total_distance, distance_sprint,
            nb_sprints, vmax, nb_acc, nb_dec, high_speed_running,
            player_load, meters_per_min, srpe_today, rpe_today,
            acute_load, chronic_load, acwr, acute_player_load,
            chronic_player_load, acwr_player_load,
            wellness_today, wellness_avg_7d, wellness_avg_28d,
            sleep_today, sleep_avg_7d, sleep_avg_28d,
            had_injury_30d, had_injury_90d, is_match_day,
            days_since_last_injury (optionnel)

    Returns:
        dict: {
            'risk_score': float (0-1),
            'risk_percent': int (0-100),
            'risk_level': str ('Faible' | 'Modere' | 'Eleve' | 'Critique'),
            'risk_color': str (Bootstrap : 'success' | 'info' | 'warning' | 'danger'),
            'will_be_injured': bool (au-dessus du seuil optimal),
            'threshold_used': float,
            'model_name': str,
        }
    """
    bundle = load_model()
    model = bundle['model']
    feature_names = bundle['feature_names']
    threshold = bundle['threshold']

    # Generer les features derivees
    features_full = engineer_features_for_prediction(player_features)

    # One-hot encoding du poste
    position = features_full.get('position', 'Milieu')
    for pos in ['Attaquant', 'Defenseur', 'Gardien', 'Milieu']:
        features_full[f'pos_{pos}'] = int(pos == position)

    # Construire le DataFrame avec les colonnes dans le bon ordre
    df = pd.DataFrame([features_full])

    # S'assurer que toutes les colonnes attendues sont presentes (sinon 0)
    for col in feature_names:
        if col not in df.columns:
            df[col] = 0
    df = df[feature_names]

    # Prediction
    risk_score = float(model.predict_proba(df)[0, 1])
    risk_percent = int(round(risk_score * 100))

    # Niveau de risque
    if risk_score >= 0.50:
        level, color = 'Critique', 'danger'
    elif risk_score >= 0.30:
        level, color = 'Eleve', 'warning'
    elif risk_score >= 0.15:
        level, color = 'Modere', 'info'
    else:
        level, color = 'Faible', 'success'

    return {
        'risk_score': risk_score,
        'risk_percent': risk_percent,
        'risk_level': level,
        'risk_color': color,
        'will_be_injured': risk_score >= threshold,
        'threshold_used': float(threshold),
        'model_name': bundle['model_name'],
    }


def predict_from_player_db(player, target_date=None):
    """
    Predit le risque pour un joueur de la base RajaTracker.
    Recupere ses donnees recentes (charges, wellness, etc.) automatiquement.

    Args:
        player: instance Player (SQLAlchemy)
        target_date (date): date de reference (par defaut : aujourd'hui)

    Returns:
        dict de predict_risk()
    """
    from app.models import TrainingResult, TrainingSession
    from datetime import date

    if target_date is None:
        target_date = date.today()

    # Calculer les features depuis l'historique du joueur
    acute_load = player.get_weekly_load()
    chronic_load = player.get_chronic_load()
    acwr = player.get_acwr()

    # Valeurs par defaut realistes si pas de donnees
    features = {
        'age': player.age if player.age else 25,
        'position': _normalize_position(player.position) if player.position else 'Milieu',
        'duration_min': 75,
        'total_distance': 4500,
        'distance_sprint': 100,
        'nb_sprints': 3,
        'vmax': 25.0,
        'nb_acc': 20,
        'nb_dec': 15,
        'high_speed_running': 350,
        'player_load': 500,
        'meters_per_min': 75,
        'srpe_today': 0,
        'rpe_today': 0,
        'acute_load': acute_load,
        'chronic_load': chronic_load,
        'acwr': acwr if acwr > 0 else 1.0,
        'acute_player_load': acute_load * 1.0,
        'chronic_player_load': chronic_load * 1.0,
        'acwr_player_load': acwr if acwr > 0 else 1.0,
        'wellness_today': 7.5,
        'wellness_avg_7d': 7.5,
        'wellness_avg_28d': 7.5,
        'sleep_today': 7.5,
        'sleep_avg_7d': 7.5,
        'sleep_avg_28d': 7.5,
        'had_injury_30d': 0,
        'had_injury_90d': 0,
        'is_match_day': 0,
        'days_since_last_injury': None,
    }

    # Recuperer la derniere seance pour les metriques recentes
    last_result = (
        TrainingResult.query
        .filter_by(player_id=player.id)
        .join(TrainingSession)
        .order_by(TrainingSession.date.desc())
        .first()
    )
    if last_result:
        if last_result.rpe:
            features['rpe_today'] = last_result.rpe
        if last_result.training_load:
            features['srpe_today'] = last_result.training_load
        if last_result.session:
            features['duration_min'] = last_result.session.duration or 75
            features['is_match_day'] = int(
                last_result.session.session_type
                and 'match' in last_result.session.session_type.lower()
            )

    return predict_risk(features)


def _normalize_position(pos):
    """Normalise le poste pour matcher les classes du modele."""
    if not pos:
        return 'Milieu'
    pos = str(pos).lower()
    if 'gardien' in pos:
        return 'Gardien'
    if 'def' in pos or 'arr' in pos:
        return 'Defenseur'
    if 'att' in pos or 'avant' in pos or 'ail' in pos:
        return 'Attaquant'
    return 'Milieu'


if __name__ == '__main__':
    # Test rapide
    print("Test du service de prediction")
    print("=" * 50)

    # Cas 1 : joueur "safe"
    safe = {
        'age': 25, 'position': 'Milieu',
        'duration_min': 75, 'total_distance': 4500,
        'distance_sprint': 80, 'nb_sprints': 2, 'vmax': 25,
        'nb_acc': 18, 'nb_dec': 14, 'high_speed_running': 300,
        'player_load': 480, 'meters_per_min': 60,
        'srpe_today': 450, 'rpe_today': 6,
        'acute_load': 2500, 'chronic_load': 2400, 'acwr': 1.04,
        'acute_player_load': 2800, 'chronic_player_load': 2700, 'acwr_player_load': 1.04,
        'wellness_today': 8, 'wellness_avg_7d': 7.8, 'wellness_avg_28d': 7.5,
        'sleep_today': 8, 'sleep_avg_7d': 7.8, 'sleep_avg_28d': 7.5,
        'had_injury_30d': 0, 'had_injury_90d': 0, 'is_match_day': 0,
        'days_since_last_injury': None,
    }
    r = predict_risk(safe)
    print(f"\nJoueur SAFE   -> {r['risk_percent']:3d}% ({r['risk_level']}, {r['risk_color']})")

    # Cas 2 : joueur a risque
    risky = {
        'age': 32, 'position': 'Defenseur',
        'duration_min': 95, 'total_distance': 6500,
        'distance_sprint': 350, 'nb_sprints': 15, 'vmax': 28,
        'nb_acc': 35, 'nb_dec': 28, 'high_speed_running': 800,
        'player_load': 820, 'meters_per_min': 68,
        'srpe_today': 855, 'rpe_today': 9,
        'acute_load': 4500, 'chronic_load': 2500, 'acwr': 1.8,
        'acute_player_load': 5000, 'chronic_player_load': 2800, 'acwr_player_load': 1.78,
        'wellness_today': 4, 'wellness_avg_7d': 4.5, 'wellness_avg_28d': 6.0,
        'sleep_today': 5, 'sleep_avg_7d': 5.5, 'sleep_avg_28d': 6.8,
        'had_injury_30d': 1, 'had_injury_90d': 1, 'is_match_day': 1,
        'days_since_last_injury': 18,
    }
    r = predict_risk(risky)
    print(f"Joueur RISKY  -> {r['risk_percent']:3d}% ({r['risk_level']}, {r['risk_color']})")

    print(f"\nModele : {load_model()['model_name']}")
    print(f"Seuil  : {load_model()['threshold']:.2f}")
