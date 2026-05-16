"""
Service d'explication des predictions de blessure.

Genere une explication lisible des raisons pour lesquelles
un joueur est a risque. Combine :
- Regles metier issues de la litterature (seuils Gabbett, Carey, etc.)
- Importance des features du modele (Random Forest)
"""


# =============================================================================
# REGLES METIER (seuils issus de la litterature scientifique)
# =============================================================================

RULES = [
    # ACWR (Gabbett 2016)
    {
        'condition': lambda f: f.get('acwr', 1.0) > 1.5,
        'message': lambda f: f"ACWR a {f['acwr']:.2f} (zone DANGER, > 1.5)",
        'icon': 'exclamation-triangle-fill',
        'color': 'danger',
        'weight': 4,
        'source': 'Gabbett 2016',
        'category': 'charge',
    },
    {
        'condition': lambda f: 1.3 < f.get('acwr', 1.0) <= 1.5,
        'message': lambda f: f"ACWR a {f['acwr']:.2f} (zone vigilance, > 1.3)",
        'icon': 'exclamation-circle-fill',
        'color': 'warning',
        'weight': 2,
        'source': 'Gabbett 2016',
        'category': 'charge',
    },
    {
        'condition': lambda f: f.get('acwr', 1.0) < 0.8,
        'message': lambda f: f"ACWR a {f['acwr']:.2f} (sous-entrainement, < 0.8)",
        'icon': 'arrow-down-circle-fill',
        'color': 'warning',
        'weight': 2,
        'source': 'Gabbett 2016',
        'category': 'charge',
    },

    # Wellness (Carey 2018)
    {
        'condition': lambda f: f.get('wellness_avg_7d', 7.5) < 5.0,
        'message': lambda f: f"Wellness 7j a {f['wellness_avg_7d']:.1f}/10 (tres bas, < 5)",
        'icon': 'emoji-frown-fill',
        'color': 'danger',
        'weight': 3,
        'source': 'Carey 2018',
        'category': 'wellness',
    },
    {
        'condition': lambda f: 5.0 <= f.get('wellness_avg_7d', 7.5) < 6.0,
        'message': lambda f: f"Wellness 7j a {f['wellness_avg_7d']:.1f}/10 (bas, < 6)",
        'icon': 'emoji-neutral-fill',
        'color': 'warning',
        'weight': 2,
        'source': 'Carey 2018',
        'category': 'wellness',
    },

    # Sommeil (Hulin 2014)
    {
        'condition': lambda f: f.get('sleep_avg_7d', 7.5) < 6.0,
        'message': lambda f: f"Sommeil 7j a {f['sleep_avg_7d']:.1f}h (insuffisant, < 6h)",
        'icon': 'moon-stars-fill',
        'color': 'danger',
        'weight': 3,
        'source': 'Hulin 2014',
        'category': 'recuperation',
    },
    {
        'condition': lambda f: 6.0 <= f.get('sleep_avg_7d', 7.5) < 7.0,
        'message': lambda f: f"Sommeil 7j a {f['sleep_avg_7d']:.1f}h (sous-optimal, < 7h)",
        'icon': 'moon-fill',
        'color': 'warning',
        'weight': 2,
        'source': 'Hulin 2014',
        'category': 'recuperation',
    },

    # Historique blessure (Drew 2017)
    {
        'condition': lambda f: (f.get('days_since_last_injury') is not None
                                and f['days_since_last_injury'] < 30),
        'message': lambda f: f"Blessure il y a {f['days_since_last_injury']} jours (< 30j)",
        'icon': 'bandaid-fill',
        'color': 'danger',
        'weight': 3,
        'source': 'Drew 2017',
        'category': 'historique',
    },
    {
        'condition': lambda f: (f.get('days_since_last_injury') is not None
                                and 30 <= f['days_since_last_injury'] < 90),
        'message': lambda f: f"Blessure il y a {f['days_since_last_injury']} jours (< 90j)",
        'icon': 'bandaid',
        'color': 'warning',
        'weight': 2,
        'source': 'Drew 2017',
        'category': 'historique',
    },

    # Charge cumulee
    {
        'condition': lambda f: f.get('acute_load', 0) > 3000,
        'message': lambda f: f"Charge aigue elevee ({f['acute_load']:.0f} UA, > 3000)",
        'icon': 'speedometer2',
        'color': 'warning',
        'weight': 2,
        'source': 'Bourdon 2017',
        'category': 'charge',
    },
    {
        'condition': lambda f: f.get('acute_player_load', 0) > 3500,
        'message': lambda f: f"Player Load aigu eleve ({f['acute_player_load']:.0f}, > 3500)",
        'icon': 'lightning-charge-fill',
        'color': 'warning',
        'weight': 2,
        'source': 'Bourdon 2017',
        'category': 'charge',
    },

    # Age
    {
        'condition': lambda f: f.get('age', 25) > 30,
        'message': lambda f: f"Age {f['age']} ans (> 30, risque accru)",
        'icon': 'person-fill',
        'color': 'info',
        'weight': 1,
        'source': 'Hagglund 2013',
        'category': 'profil',
    },
]


# =============================================================================
# FACTEURS POSITIFS (ce qui va bien)
# =============================================================================

POSITIVES = [
    {
        'condition': lambda f: 0.8 <= f.get('acwr', 1.0) <= 1.3,
        'message': lambda f: f"ACWR a {f['acwr']:.2f} (zone optimale 0.8-1.3)",
        'icon': 'check-circle-fill',
    },
    {
        'condition': lambda f: f.get('wellness_avg_7d', 7.5) >= 7.0,
        'message': lambda f: f"Wellness excellent ({f['wellness_avg_7d']:.1f}/10)",
        'icon': 'emoji-smile-fill',
    },
    {
        'condition': lambda f: f.get('sleep_avg_7d', 7.5) >= 7.5,
        'message': lambda f: f"Sommeil suffisant ({f['sleep_avg_7d']:.1f}h)",
        'icon': 'moon-stars-fill',
    },
    {
        'condition': lambda f: (f.get('days_since_last_injury') is None
                                or f['days_since_last_injury'] >= 180),
        'message': lambda f: "Pas de blessure recente (> 180j)",
        'icon': 'shield-fill-check',
    },
]


# =============================================================================
# RECOMMANDATIONS
# =============================================================================

def get_recommendations(risk_factors):
    """Genere des recommandations basees sur les facteurs de risque detectes."""
    recs = []
    categories = {rf['category'] for rf in risk_factors}

    if 'charge' in categories:
        recs.append({
            'icon': 'speedometer2',
            'text': "Reduire la charge d'entrainement de 15-20% cette semaine",
            'priority': 'high',
        })
    if 'wellness' in categories:
        recs.append({
            'icon': 'heart-pulse-fill',
            'text': "Suivi medical et entretien avec le joueur (signaux subjectifs degrades)",
            'priority': 'high',
        })
    if 'recuperation' in categories:
        recs.append({
            'icon': 'moon-fill',
            'text': "Renforcer le protocole sommeil (objectif >= 7h30/nuit)",
            'priority': 'medium',
        })
    if 'historique' in categories:
        recs.append({
            'icon': 'bandaid-fill',
            'text': "Verification kine + adaptation progressive de la charge",
            'priority': 'high',
        })
    if 'profil' in categories:
        recs.append({
            'icon': 'person-fill',
            'text': "Renforcement musculaire prophylactique adapte (joueur experimente)",
            'priority': 'medium',
        })

    if not recs:
        recs.append({
            'icon': 'check-circle-fill',
            'text': "Continuer sur cette dynamique, profil tres favorable",
            'priority': 'info',
        })
    return recs


# =============================================================================
# FONCTION PRINCIPALE
# =============================================================================

def explain_prediction(features, prediction):
    """
    Explique pourquoi un joueur est a risque.

    Args:
        features (dict): features utilisees pour la prediction
        prediction (dict): resultat de predict_risk()

    Returns:
        dict: {
            'risk_factors': [list de facteurs de risque],
            'positive_factors': [list de facteurs positifs],
            'recommendations': [list de recommandations],
            'summary': str
        }
    """
    # Facteurs de risque actifs
    risk_factors = []
    for rule in RULES:
        try:
            if rule['condition'](features):
                risk_factors.append({
                    'message': rule['message'](features),
                    'icon': rule['icon'],
                    'color': rule['color'],
                    'weight': rule['weight'],
                    'source': rule['source'],
                    'category': rule['category'],
                })
        except Exception:
            continue
    # Trier par poids
    risk_factors.sort(key=lambda x: x['weight'], reverse=True)

    # Facteurs positifs
    positive_factors = []
    for rule in POSITIVES:
        try:
            if rule['condition'](features):
                positive_factors.append({
                    'message': rule['message'](features),
                    'icon': rule['icon'],
                })
        except Exception:
            continue

    # Recommandations
    recommendations = get_recommendations(risk_factors)

    # Resume textuel
    risk_pct = prediction['risk_percent']
    if risk_pct >= 50:
        summary = f"Risque CRITIQUE ({risk_pct}%) : {len(risk_factors)} facteurs de risque detectes. Action immediate recommandee."
    elif risk_pct >= 30:
        summary = f"Risque ELEVE ({risk_pct}%) : {len(risk_factors)} facteurs a surveiller de pres."
    elif risk_pct >= 15:
        summary = f"Risque MODERE ({risk_pct}%). Surveillance recommandee."
    else:
        summary = f"Risque FAIBLE ({risk_pct}%). Profil tres favorable."

    return {
        'risk_factors': risk_factors,
        'positive_factors': positive_factors,
        'recommendations': recommendations,
        'summary': summary,
    }


if __name__ == '__main__':
    from app.ml.predict import predict_risk

    print("Test du service d'explication")
    print("=" * 60)

    # Joueur a risque
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

    pred = predict_risk(risky)
    explanation = explain_prediction(risky, pred)

    print(f"\n{explanation['summary']}")

    print(f"\n--- {len(explanation['risk_factors'])} FACTEURS DE RISQUE ---")
    for rf in explanation['risk_factors']:
        print(f"  [{rf['color'].upper():8}] {rf['message']} ({rf['source']})")

    print(f"\n--- {len(explanation['positive_factors'])} FACTEURS POSITIFS ---")
    for pf in explanation['positive_factors']:
        print(f"  [POSITIF ] {pf['message']}")

    print(f"\n--- RECOMMANDATIONS ---")
    for rec in explanation['recommendations']:
        print(f"  [{rec['priority'].upper():6}] {rec['text']}")
