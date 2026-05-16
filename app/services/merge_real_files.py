"""
Fusionne les 4 fichiers Excel Catapult en UN SEUL fichier maitre.

Sources (dans ml_data/raw_real_data/) :
- CHBILI.xlsx       -> 1 feuille  (Ismail CHBILI)
- AMEHMOUL.xlsx     -> 1 feuille  (Mehdi AMEHMOUL)
- RCA.xlsx          -> 3 feuilles (Adam ABID + Ismail CHBILI + Ammar BOULKAMH)
- Data_GPS_IGUIZ_2.xlsx -> 1 feuille (Yahya IGUIZ)

Resultat (ml_data/) :
- MAROC_RCA_All_Data.xlsx : toutes les seances regroupees,
  meme structure de colonnes que les fichiers sources.

Usage :
    python -m app.services.merge_real_files
"""

import os
import pandas as pd
from pathlib import Path


SOURCE_DIR = 'ml_data/raw_real_data'
OUTPUT_FILE = 'ml_data/MAROC_RCA_All_Data.xlsx'


def merge_all_files():
    print("=" * 70)
    print("FUSION DES FICHIERS CATAPULT EN UN SEUL")
    print("=" * 70)

    source_dir = Path(SOURCE_DIR)
    if not source_dir.exists():
        print(f"ERREUR : dossier {SOURCE_DIR} introuvable")
        return

    all_records = []
    files_found = []

    # Parcourir tous les fichiers Excel du dossier
    for filepath in sorted(source_dir.glob('*.xlsx')):
        if filepath.name.startswith('~$'):
            continue
        files_found.append(filepath.name)
        print(f"\n[*] Lecture : {filepath.name}")

        # Lire toutes les feuilles
        try:
            all_sheets = pd.read_excel(filepath, sheet_name=None)
        except Exception as e:
            print(f"   ! Erreur : {e}")
            continue

        for sheet_name, df in all_sheets.items():
            if df.empty:
                continue
            # Garder seulement les lignes avec un nom de joueur
            if 'Name' not in df.columns:
                print(f"   ! Feuille '{sheet_name}' : colonne 'Name' absente, ignoree")
                continue

            df_clean = df.dropna(subset=['Name'])
            if df_clean.empty:
                continue

            all_records.append(df_clean)
            unique_players = df_clean['Name'].unique()
            print(f"   - Feuille '{sheet_name}' : {len(df_clean)} lignes, joueurs : {', '.join(unique_players)}")

    if not all_records:
        print("\nERREUR : aucun enregistrement trouve")
        return

    # Concatener tous les DataFrames
    print(f"\n[*] Fusion de {len(all_records)} feuilles...")
    merged = pd.concat(all_records, ignore_index=True, sort=False)

    # Trier par date puis par joueur
    if 'Date' in merged.columns:
        merged = merged.sort_values(by=['Date', 'Name'], na_position='last')

    # Sauvegarder
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    merged.to_excel(OUTPUT_FILE, index=False, sheet_name='All_Sessions')

    # Resume
    print(f"\n{'=' * 70}")
    print("RESUME")
    print(f"{'=' * 70}")
    print(f"Fichiers sources   : {len(files_found)}")
    for f in files_found:
        print(f"  - {f}")
    print(f"\nFichier fusionne   : {OUTPUT_FILE}")
    print(f"Total seances      : {len(merged)}")
    print(f"Joueurs uniques    : {merged['Name'].nunique()}")
    print(f"  Liste : {', '.join(sorted(merged['Name'].dropna().unique()))}")
    if 'Date' in merged.columns:
        dates_clean = pd.to_datetime(merged['Date'], errors='coerce').dropna()
        if not dates_clean.empty:
            print(f"\nPeriode couverte   : {dates_clean.min().date()} -> {dates_clean.max().date()}")
    print(f"\nVous pouvez maintenant importer ce fichier unique via /gps/upload")


if __name__ == '__main__':
    merge_all_files()
