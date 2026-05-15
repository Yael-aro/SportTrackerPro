"""
Analyse des donnees GPS reelles (Catapult Sports) pour calibrer le generateur synthetique.

Lit tous les fichiers Excel dans ml_data/raw_real_data/, consolide les seances,
calcule les statistiques par poste, et sauvegarde un fichier JSON de calibration.
"""

import os
import json
import pandas as pd
import numpy as np

REAL_DATA_DIR = 'ml_data/raw_real_data'
OUTPUT_JSON = 'ml_data/calibration_stats.json'
CONSOLIDATED_CSV = 'ml_data/real_data_consolidated.csv'


def load_all_real_data():
    """Charge tous les fichiers Excel et concatene en un DataFrame unique."""
    all_dfs = []

    for filename in sorted(os.listdir(REAL_DATA_DIR)):
        if not filename.endswith('.xlsx'):
            continue

        filepath = os.path.join(REAL_DATA_DIR, filename)
        print(f"  Lecture: {filename}")

        try:
            sheets = pd.read_excel(filepath, sheet_name=None)
            for sheet_name, df in sheets.items():
                df['_source_file'] = filename
                df['_source_sheet'] = sheet_name
                all_dfs.append(df)
        except Exception as e:
            print(f"    ERREUR: {e}")

    if not all_dfs:
        raise RuntimeError("Aucun fichier Excel trouve dans " + REAL_DATA_DIR)

    combined = pd.concat(all_dfs, ignore_index=True, sort=False)
    return combined


def clean_data(df):
    """Nettoie le DataFrame : conversion dates, suppression lignes vides, etc."""
    # Garder seulement les lignes avec un nom de joueur
    df = df[df['Name'].notna()].copy()

    # Convertir Date (formats mixtes)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce', dayfirst=True)
    df = df[df['Date'].notna()]

    # Renommer colonnes pour faciliter
    rename_map = {
        'Durée (min)': 'duration_min',
        'TD (m)': 'total_distance',
        'TD 0-7km/h (m)': 'distance_walk',
        'TD 7-15km/h (m)': 'distance_jog',
        'TD 15-20km/h (m)': 'distance_run',
        'TD 20-25km/h (m)': 'distance_fast',
        'TD >25km/h (m)': 'distance_sprint',
        'Sprint >25km/h (nb)': 'nb_sprints',
        'Vmax (km/h)': 'vmax',
        'Acc >3m/s2 (nb)': 'nb_acc',
        'Acc max (m/s2)': 'acc_max',
        'Dec <-3m/s2 (nb)': 'nb_dec',
        'Dec max (m/s2)': 'dec_max',
        'Acc + Dec (nb)': 'nb_acc_dec',
        'm/min': 'meters_per_min',
        'HID >15km/h (m)': 'high_intensity_dist',
        'HSR >20km/h (m)': 'high_speed_running',
        'MPE >20W/kg (nb)': 'metabolic_power_events',
        'Energy': 'energy',
        'Meta Energy (KJ/kg)': 'meta_energy',
        'EDI (%)': 'edi_percent',
        'Player Load (UA)': 'player_load',
        'Jump (nb)': 'nb_jumps',
        'Poste': 'position',
        'Equipe': 'team',
        'Activité': 'session_type',
    }
    df = df.rename(columns=rename_map)
    return df


def normalize_position(pos):
    """Standardise les postes en 4 categories : Gardien / Defenseur / Milieu / Attaquant."""
    if pd.isna(pos):
        return 'Inconnu'
    pos = str(pos).lower()
    if 'gardien' in pos or 'goal' in pos:
        return 'Gardien'
    if 'defens' in pos or 'arr' in pos:
        return 'Defenseur'
    if 'milieu' in pos or 'mid' in pos:
        return 'Milieu'
    if 'attaq' in pos or 'avant' in pos or 'ail' in pos:
        return 'Attaquant'
    return 'Milieu'  # defaut


def compute_calibration_stats(df):
    """Calcule moyennes et ecarts-types par poste pour calibrer le generateur."""
    df['position_normalized'] = df['position'].apply(normalize_position)

    metrics = [
        'duration_min', 'total_distance', 'distance_sprint', 'nb_sprints',
        'vmax', 'nb_acc', 'nb_dec', 'high_speed_running', 'player_load',
        'meters_per_min',
    ]

    # Stats globales
    global_stats = {}
    for m in metrics:
        if m in df.columns:
            values = pd.to_numeric(df[m], errors='coerce').dropna()
            if len(values) > 0:
                global_stats[m] = {
                    'mean': float(values.mean()),
                    'std': float(values.std()) if len(values) > 1 else 0.0,
                    'min': float(values.min()),
                    'max': float(values.max()),
                    'median': float(values.median()),
                }

    # Stats par poste
    per_position = {}
    for pos in df['position_normalized'].unique():
        pos_df = df[df['position_normalized'] == pos]
        per_position[pos] = {}
        for m in metrics:
            if m in pos_df.columns:
                values = pd.to_numeric(pos_df[m], errors='coerce').dropna()
                if len(values) > 0:
                    per_position[pos][m] = {
                        'mean': float(values.mean()),
                        'std': float(values.std()) if len(values) > 1 else 0.0,
                        'count': int(len(values)),
                    }

    return {
        'global': global_stats,
        'per_position': per_position,
        'n_total_sessions': int(len(df)),
        'n_players': int(df['Name'].nunique()),
        'players': sorted(df['Name'].unique().tolist()),
        'positions_distribution': df['position_normalized'].value_counts().to_dict(),
        'date_range': {
            'start': str(df['Date'].min().date()) if df['Date'].notna().any() else None,
            'end': str(df['Date'].max().date()) if df['Date'].notna().any() else None,
        },
    }


def main():
    print("=" * 70)
    print("ANALYSE DES DONNEES GPS REELLES (Catapult Sports)")
    print("=" * 70)

    print("\n[1/3] Chargement des fichiers Excel...")
    df = load_all_real_data()
    print(f"   -> {len(df)} lignes brutes chargees")

    print("\n[2/3] Nettoyage...")
    df = clean_data(df)
    print(f"   -> {len(df)} lignes apres nettoyage")
    print(f"   -> {df['Name'].nunique()} joueurs uniques")

    # Sauvegarder le CSV consolide
    df.to_csv(CONSOLIDATED_CSV, index=False)
    print(f"   -> CSV consolide : {CONSOLIDATED_CSV}")

    print("\n[3/3] Calcul des statistiques de calibration...")
    stats = compute_calibration_stats(df)

    # Sauvegarder JSON
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"   -> Stats sauvegardees : {OUTPUT_JSON}")

    # Resume
    print("\n" + "=" * 70)
    print("RESUME")
    print("=" * 70)
    print(f"Joueurs           : {stats['n_players']}")
    print(f"Seances           : {stats['n_total_sessions']}")
    print(f"Periode           : {stats['date_range']['start']} -> {stats['date_range']['end']}")
    print(f"Postes            : {stats['positions_distribution']}")
    print(f"\nDistance totale moyenne : {stats['global']['total_distance']['mean']:.0f} m (sd={stats['global']['total_distance']['std']:.0f})")
    print(f"Vmax moyenne            : {stats['global']['vmax']['mean']:.2f} km/h")
    print(f"Player Load moyen       : {stats['global']['player_load']['mean']:.0f} UA")
    print(f"Sprints moyens / seance : {stats['global']['nb_sprints']['mean']:.1f}")

    print("\nPar poste :")
    for pos, pos_stats in stats['per_position'].items():
        if 'total_distance' in pos_stats:
            print(f"  {pos:12} : TD={pos_stats['total_distance']['mean']:.0f}m, "
                  f"PL={pos_stats['player_load']['mean']:.0f}UA "
                  f"(n={pos_stats['total_distance']['count']})")


if __name__ == '__main__':
    main()
