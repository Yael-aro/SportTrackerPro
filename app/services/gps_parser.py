"""
Parser GPS Universel
====================
Detecte automatiquement le fournisseur (Catapult FR/EN, STATSports, Playertek, GPExe)
en analysant les noms de colonnes du fichier importe, et applique le bon mapping.

Avantage : RajaTracker est agnostique au fournisseur. Le club peut changer de
Catapult vers STATSports sans recoder quoi que ce soit.
"""

import pandas as pd
from difflib import SequenceMatcher


# =============================================================================
# SIGNATURES DES FOURNISSEURS GPS
# =============================================================================
# Chaque fournisseur a des colonnes caracteristiques. On les utilise pour detecter
# le format du fichier importe.

PROVIDER_SIGNATURES = {
    'Catapult_FR': {
        'display_name': 'Catapult Sports (FR)',
        'key_columns': ['TD (m)', 'Vmax (km/h)', 'Player Load (UA)', 'Sprint >25km/h (nb)'],
        'min_match': 2,  # au moins 2 colonnes doivent matcher
        'mapping': {
            'player_name': 'Name',
            'date': 'Date',
            'duration': 'Durée (min)',
            'session_type': 'Activité',
            'position': 'Poste',
            'team': 'Equipe',
            'total_distance': 'TD (m)',
            'distance_walk': 'TD 0-7km/h (m)',
            'distance_jog': 'TD 7-15km/h (m)',
            'distance_run': 'TD 15-20km/h (m)',
            'distance_fast': 'TD 20-25km/h (m)',
            'sprint_distance': 'TD >25km/h (m)',
            'hsr_distance': 'HSR >20km/h (m)',
            'nb_sprints': 'Sprint >25km/h (nb)',
            'max_speed': 'Vmax (km/h)',
            'avg_speed': 'm/min',
            'player_load': 'Player Load (UA)',
            'accelerations': 'Acc >3m/s2 (nb)',
            'decelerations': 'Dec <-3m/s2 (nb)',
            'energy': 'Energy',
            'meta_energy': 'Meta Energy (KJ/kg)',
            'edi_percent': 'EDI (%)',
            'nb_jumps': 'Jump (nb)',
        }
    },
    'Catapult_EN': {
        'display_name': 'Catapult Sports (EN)',
        'key_columns': ['Total Distance', 'Player Load', 'Max Velocity', 'Acceleration Count'],
        'min_match': 2,
        'mapping': {
            'player_name': 'Player Name',
            'total_distance': 'Total Distance',
            'hsr_distance': 'HSR Distance',
            'sprint_distance': 'Sprint Distance',
            'max_speed': 'Max Velocity',
            'avg_speed': 'Avg Velocity',
            'player_load': 'Player Load',
            'accelerations': 'Acceleration Count',
            'decelerations': 'Deceleration Count',
            'hr_avg': 'Avg HR',
            'hr_max': 'Max HR',
        }
    },
    'STATSports': {
        'display_name': 'STATSports',
        'key_columns': ['Distance (m)', 'HSR (m)', 'Dynamic Stress Load', 'Max Speed (km/h)'],
        'min_match': 2,
        'mapping': {
            'player_name': 'Player',
            'total_distance': 'Distance (m)',
            'hsr_distance': 'HSR (m)',
            'sprint_distance': 'Sprint Distance (m)',
            'max_speed': 'Max Speed (km/h)',
            'player_load': 'Dynamic Stress Load',
            'hr_avg': 'Avg Heart Rate',
            'hr_max': 'Max Heart Rate',
        }
    },
    'Playertek': {
        'display_name': 'Playertek',
        'key_columns': ['Name', 'Total Distance', 'High Speed Running', 'Top Speed'],
        'min_match': 3,  # plus strict car colonnes generiques
        'mapping': {
            'player_name': 'Name',
            'total_distance': 'Total Distance',
            'hsr_distance': 'High Speed Running',
            'sprint_distance': 'Sprint',
            'max_speed': 'Top Speed',
            'player_load': 'Load',
        }
    },
    'GPExe': {
        'display_name': 'GPExe',
        'key_columns': ['Athlete', 'Distance', 'Distance Z5', 'Vmax', 'Equivalent Distance'],
        'min_match': 3,
        'mapping': {
            'player_name': 'Athlete',
            'total_distance': 'Distance',
            'hsr_distance': 'Distance Z5',
            'sprint_distance': 'Distance Z6',
            'max_speed': 'Vmax',
            'player_load': 'Equivalent Distance',
        }
    },
}


# =============================================================================
# AUTO-DETECTION
# =============================================================================

def auto_detect_provider(columns):
    """
    Analyse les noms de colonnes et retourne le fournisseur le plus probable.

    Args:
        columns: liste de noms de colonnes du fichier (ex: ['Name', 'TD (m)', ...])

    Returns:
        tuple (provider_key, confidence_score, signature_dict)
        - provider_key   : 'Catapult_FR' / 'STATSports' / ... ou None si inconnu
        - confidence     : 0.0 a 1.0 (combien de colonnes ont matche)
        - signature_dict : la signature complete pour ensuite mapper les donnees
    """
    columns_set = set(c.strip() for c in columns if isinstance(c, str))
    columns_lower = set(c.lower() for c in columns_set)

    scores = {}

    for provider, sig in PROVIDER_SIGNATURES.items():
        matches = 0
        for key_col in sig['key_columns']:
            # Match exact
            if key_col in columns_set:
                matches += 1
            # Match insensible a la casse
            elif key_col.lower() in columns_lower:
                matches += 0.8

        if matches >= sig['min_match']:
            scores[provider] = matches / len(sig['key_columns'])

    if not scores:
        return None, 0.0, None

    # Le fournisseur avec le meilleur score gagne
    best = max(scores, key=scores.get)
    return best, scores[best], PROVIDER_SIGNATURES[best]


# =============================================================================
# LECTURE DU FICHIER
# =============================================================================

def read_gps_file(filepath):
    """
    Lit un fichier GPS (.xlsx, .xls ou .csv) et retourne une LISTE de DataFrames.
    - Pour un CSV : retourne [df]
    - Pour un Excel mono-feuille : retourne [df]
    - Pour un Excel multi-feuilles (RCA.xlsx) : retourne [df_feuille1, df_feuille2, ...]
    """
    if filepath.endswith('.csv'):
        return [pd.read_csv(filepath)]

    if filepath.endswith(('.xlsx', '.xls')):
        # Lire toutes les feuilles
        all_sheets = pd.read_excel(filepath, sheet_name=None)
        return [df for df in all_sheets.values() if not df.empty]

    raise ValueError(f"Format non supporte : {filepath}")


def parse_file_with_autodetect(filepath):
    """
    Lit un fichier GPS, detecte automatiquement le fournisseur, et retourne
    une structure normalisee prete a etre importee en BDD.

    Returns:
        dict {
            'provider': str (ex: 'Catapult_FR'),
            'display_name': str (ex: 'Catapult Sports (FR)'),
            'confidence': float (0-1),
            'sheets_count': int,
            'records': list de dicts {colonne_standardisee: valeur},
            'unknown_columns': list (colonnes non mappees),
            'warnings': list,
        }
    """
    dfs = read_gps_file(filepath)
    if not dfs:
        return {'error': 'Fichier vide'}

    # Auto-detection sur la PREMIERE feuille (on suppose que toutes les feuilles
    # ont la meme structure dans un Excel Catapult multi-joueurs)
    first_df = dfs[0]
    provider, confidence, signature = auto_detect_provider(list(first_df.columns))

    if provider is None:
        return {
            'error': 'Fournisseur GPS non reconnu',
            'columns_found': list(first_df.columns),
            'sheets_count': len(dfs),
        }

    mapping = signature['mapping']

    # Parcourir toutes les feuilles et normaliser les donnees
    all_records = []
    warnings = []
    unknown_cols = set()

    for sheet_idx, df in enumerate(dfs):
        for _, row in df.iterrows():
            record = {'_sheet': sheet_idx}

            # Mapper colonne par colonne
            for standard_field, source_col in mapping.items():
                if source_col in df.columns:
                    value = row.get(source_col)
                    # Nettoyer NaN
                    if pd.isna(value):
                        value = None
                    record[standard_field] = value
                else:
                    record[standard_field] = None

            # Identifier les colonnes inconnues
            for col in df.columns:
                if col not in mapping.values() and not pd.isna(row.get(col)):
                    unknown_cols.add(col)

            # Garder seulement les enregistrements avec un nom de joueur
            if record.get('player_name'):
                all_records.append(record)

    return {
        'provider': provider,
        'display_name': signature['display_name'],
        'confidence': round(confidence, 2),
        'sheets_count': len(dfs),
        'records': all_records,
        'records_count': len(all_records),
        'unknown_columns': sorted(unknown_cols),
        'warnings': warnings,
    }


if __name__ == '__main__':
    import sys
    import os

    # Test rapide avec un fichier reel
    test_files = [
        'ml_data/raw_real_data/CHBILI.xlsx',
        'ml_data/raw_real_data/AMEHMOUL.xlsx',
        'ml_data/raw_real_data/RCA.xlsx',
        'ml_data/raw_real_data/Data_GPS_IGUIZ_2.xlsx',
    ]

    for f in test_files:
        if not os.path.exists(f):
            continue
        print(f"\n{'='*70}")
        print(f"FICHIER : {f}")
        print('='*70)

        try:
            result = parse_file_with_autodetect(f)

            if 'error' in result:
                print(f"  ERREUR : {result['error']}")
                if 'columns_found' in result:
                    print(f"  Colonnes trouvees : {result['columns_found'][:5]}...")
                continue

            print(f"  Detecte         : {result['display_name']} ({result['provider']})")
            print(f"  Confiance       : {result['confidence']*100:.0f}%")
            print(f"  Feuilles        : {result['sheets_count']}")
            print(f"  Enregistrements : {result['records_count']}")
            print(f"  Colonnes inconnues : {len(result['unknown_columns'])}")

            if result['records']:
                # Afficher le premier enregistrement
                first = result['records'][0]
                print(f"\n  Premier enregistrement :")
                print(f"    Joueur         : {first.get('player_name')}")
                print(f"    Date           : {first.get('date')}")
                print(f"    Activite       : {first.get('session_type')}")
                print(f"    Equipe         : {first.get('team')}")
                print(f"    Poste          : {first.get('position')}")
                print(f"    Duree (min)    : {first.get('duration')}")
                print(f"    Distance totale: {first.get('total_distance')} m")
                print(f"    Vmax           : {first.get('max_speed')} km/h")
                print(f"    Player Load    : {first.get('player_load')} UA")

        except Exception as e:
            print(f"  EXCEPTION : {e}")
