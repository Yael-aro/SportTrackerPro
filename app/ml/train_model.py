"""
Entrainement du modele de prediction de blessure (version amelioree).

Ameliorations :
- Features derivees (ratios, interactions, indicateurs de tendance)
- Hyperparametres optimises (200 -> 500 arbres, profondeur ajustee)
- Comparaison Random Forest + Gradient Boosting + XGBoost
- Stratification preservant le ratio de classes
"""

import os
import json
import numpy as np
import pandas as pd
import joblib
from datetime import datetime

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    roc_auc_score, classification_report, confusion_matrix,
    precision_recall_fscore_support
)

import xgboost as xgb

DATASET_PATH = 'ml_data/training_dataset.csv'
MODEL_OUTPUT = 'ml_models/injury_predictor.joblib'
METRICS_OUTPUT = 'ml_models/metrics.json'
FEATURE_IMPORTANCE_OUTPUT = 'ml_models/feature_importance.json'

BASE_FEATURES = [
    'age',
    'duration_min', 'total_distance', 'distance_sprint', 'nb_sprints',
    'vmax', 'nb_acc', 'nb_dec', 'high_speed_running', 'player_load',
    'meters_per_min',
    'srpe_today', 'rpe_today',
    'acute_load', 'chronic_load', 'acwr',
    'acute_player_load', 'chronic_player_load', 'acwr_player_load',
    'wellness_today', 'wellness_avg_7d', 'wellness_avg_28d',
    'sleep_today', 'sleep_avg_7d', 'sleep_avg_28d',
    'had_injury_30d', 'had_injury_90d',
    'is_match_day',
]

TARGET = 'injured_within_7d'


def engineer_features(df):
    """
    Ajoute des features derivees pour aider le modele a apprendre.
    Ces transformations sont basees sur la litterature scientifique.
    """
    print("   -> Ajout de features derivees...")

    # 1. Indicateurs binaires de zones de risque (Gabbett)
    df['acwr_danger'] = (df['acwr'] > 1.5).astype(int)
    df['acwr_warning'] = ((df['acwr'] > 1.3) & (df['acwr'] <= 1.5)).astype(int)
    df['acwr_undertraining'] = (df['acwr'] < 0.8).astype(int)
    df['acwr_optimal'] = ((df['acwr'] >= 0.8) & (df['acwr'] <= 1.3)).astype(int)

    # 2. Wellness en zones (Carey)
    df['wellness_low'] = (df['wellness_avg_7d'] < 5.0).astype(int)
    df['wellness_medium'] = ((df['wellness_avg_7d'] >= 5.0) & (df['wellness_avg_7d'] < 6.0)).astype(int)

    # 3. Sommeil en zones (Hulin)
    df['sleep_insufficient'] = (df['sleep_avg_7d'] < 6.0).astype(int)
    df['sleep_suboptimal'] = ((df['sleep_avg_7d'] >= 6.0) & (df['sleep_avg_7d'] < 7.0)).astype(int)

    # 4. Tendances : difference entre aigu et chronique (deviation par rapport a l'habitude)
    df['wellness_trend'] = df['wellness_avg_7d'] - df['wellness_avg_28d']
    df['sleep_trend'] = df['sleep_avg_7d'] - df['sleep_avg_28d']

    # 5. Charge cumulee en zones
    df['acute_load_high'] = (df['acute_load'] > 3000).astype(int)
    df['acute_pl_high'] = (df['acute_player_load'] > 3500).astype(int)

    # 6. Combinaisons multi-facteurs (interactions)
    # Wellness ET ACWR mauvais ensemble = double penalite
    df['double_risk_wellness_acwr'] = (
        (df['wellness_avg_7d'] < 6.0) & (df['acwr'] > 1.3)
    ).astype(int)

    # Sommeil ET historique blessure
    df['double_risk_sleep_injury'] = (
        (df['sleep_avg_7d'] < 6.5) & (df['had_injury_30d'] == 1)
    ).astype(int)

    # Triple risque
    df['triple_risk'] = (
        (df['wellness_avg_7d'] < 6.0) &
        (df['acwr'] > 1.3) &
        (df['sleep_avg_7d'] < 7.0)
    ).astype(int)

    # 7. Score de stress total
    df['stress_score'] = (
        df['acwr_danger'] * 3 +
        df['acwr_warning'] * 2 +
        df['wellness_low'] * 2 +
        df['sleep_insufficient'] * 2 +
        df['had_injury_30d'] * 2 +
        df['acute_load_high'] * 1
    )

    # 8. Ratios derives
    df['sprint_per_min'] = df['distance_sprint'] / (df['duration_min'] + 1)
    df['load_per_min'] = df['player_load'] / (df['duration_min'] + 1)

    # 9. Age binaire (jeune ou vieux)
    df['age_young'] = (df['age'] < 20).astype(int)
    df['age_old'] = (df['age'] > 30).astype(int)

    # 10. Combine jours-depuis-blessure de maniere continue
    df['days_since_injury_filled'] = df['days_since_last_injury'].fillna(365)
    df['recent_injury_log'] = np.log1p(365 - df['days_since_injury_filled'].clip(0, 365))

    return df


def load_and_prepare_data():
    print("\n[1/6] Chargement et preparation des donnees...")
    df = pd.read_csv(DATASET_PATH)
    print(f"   -> {len(df):,} lignes")
    print(f"   -> Taux blessure : {df[TARGET].mean()*100:.2f}%")

    # Feature engineering
    df = engineer_features(df)

    # One-hot encoding pour position
    df = pd.get_dummies(df, columns=['position'], prefix='pos')
    position_cols = [c for c in df.columns if c.startswith('pos_')]

    derived_features = [
        'acwr_danger', 'acwr_warning', 'acwr_undertraining', 'acwr_optimal',
        'wellness_low', 'wellness_medium',
        'sleep_insufficient', 'sleep_suboptimal',
        'wellness_trend', 'sleep_trend',
        'acute_load_high', 'acute_pl_high',
        'double_risk_wellness_acwr', 'double_risk_sleep_injury', 'triple_risk',
        'stress_score',
        'sprint_per_min', 'load_per_min',
        'age_young', 'age_old',
        'days_since_injury_filled', 'recent_injury_log',
    ]

    features_full = BASE_FEATURES + derived_features + position_cols
    X = df[features_full]
    y = df[TARGET]

    print(f"   -> {len(features_full)} features (dont {len(derived_features)} derivees)")
    return X, y, features_full


def train_random_forest(X_train, y_train):
    print("\n[2/6] Random Forest (500 arbres)...")
    model = RandomForestClassifier(
        n_estimators=500,
        max_depth=20,
        min_samples_split=10,
        min_samples_leaf=5,
        max_features='sqrt',
        class_weight='balanced',
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    return model


def train_gradient_boosting(X_train, y_train):
    print("\n[3/6] Gradient Boosting (300 arbres)...")
    model = GradientBoostingClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42,
    )
    model.fit(X_train, y_train)
    return model


def train_xgboost(X_train, y_train):
    print("\n[4/6] XGBoost (500 arbres)...")
    n_neg = (y_train == 0).sum()
    n_pos = (y_train == 1).sum()
    scale_pos_weight = n_neg / max(n_pos, 1)

    model = xgb.XGBClassifier(
        n_estimators=500,
        max_depth=7,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        eval_metric='auc',
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train, verbose=False)
    return model


def evaluate(model, model_name, X_test, y_test):
    y_proba = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_proba)

    # Seuil optimal F1
    thresholds = np.arange(0.1, 0.9, 0.02)
    best_f1 = 0
    best_threshold = 0.5
    for t in thresholds:
        y_pred = (y_proba >= t).astype(int)
        _, _, f1, _ = precision_recall_fscore_support(
            y_test, y_pred, average='binary', zero_division=0
        )
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = t

    y_pred = (y_proba >= best_threshold).astype(int)
    cm = confusion_matrix(y_test, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average='binary', zero_division=0
    )

    print(f"\n   === {model_name} (seuil={best_threshold:.2f}) ===")
    print(f"   AUC : {auc:.4f}   Precision : {precision:.3f}   Recall : {recall:.3f}   F1 : {f1:.3f}")
    print(f"   TN={cm[0,0]:5d}  FP={cm[0,1]:5d}  |  FN={cm[1,0]:5d}  TP={cm[1,1]:5d}")

    return {
        'auc': float(auc),
        'precision': float(precision),
        'recall': float(recall),
        'f1': float(f1),
        'threshold': float(best_threshold),
        'confusion_matrix': cm.tolist(),
    }, y_proba


def main():
    print("=" * 70)
    print("ENTRAINEMENT DU MODELE (version amelioree)")
    print("=" * 70)

    X, y, features_full = load_and_prepare_data()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"   Train : {len(X_train):,}   Test : {len(X_test):,}")

    rf = train_random_forest(X_train, y_train)
    gb = train_gradient_boosting(X_train, y_train)
    xb = train_xgboost(X_train, y_train)

    print("\n[5/6] Evaluation...")
    rf_metrics, rf_proba = evaluate(rf, "Random Forest", X_test, y_test)
    gb_metrics, gb_proba = evaluate(gb, "Gradient Boosting", X_test, y_test)
    xb_metrics, xb_proba = evaluate(xb, "XGBoost", X_test, y_test)

    # Meilleur modele
    models = [
        ('RandomForest', rf, rf_metrics),
        ('GradientBoosting', gb, gb_metrics),
        ('XGBoost', xb, xb_metrics),
    ]
    best_name, best_model, best_metrics = max(models, key=lambda x: x[2]['auc'])

    print("\n[6/6] Sauvegarde du meilleur modele...")
    print(f"   -> {best_name} (AUC = {best_metrics['auc']:.4f})")

    os.makedirs(os.path.dirname(MODEL_OUTPUT), exist_ok=True)
    bundle = {
        'model': best_model,
        'model_name': best_name,
        'feature_names': features_full,
        'threshold': best_metrics['threshold'],
        'trained_at': datetime.now().isoformat(),
    }
    joblib.dump(bundle, MODEL_OUTPUT)

    all_metrics = {
        'best_model': best_name,
        'random_forest': rf_metrics,
        'gradient_boosting': gb_metrics,
        'xgboost': xb_metrics,
        'n_train': int(len(X_train)),
        'n_test': int(len(X_test)),
        'n_features': len(features_full),
        'trained_at': datetime.now().isoformat(),
    }
    with open(METRICS_OUTPUT, 'w') as f:
        json.dump(all_metrics, f, indent=2)

    # Importance
    importances = best_model.feature_importances_
    importance_list = sorted(
        zip(features_full, importances),
        key=lambda x: x[1],
        reverse=True
    )
    importance = [{'feature': f, 'importance': float(i)} for f, i in importance_list]
    with open(FEATURE_IMPORTANCE_OUTPUT, 'w') as f:
        json.dump(importance, f, indent=2)

    # Top 15
    print(f"\n{'=' * 70}")
    print(f"TOP 15 FACTEURS DE RISQUE ({best_name})")
    print(f"{'=' * 70}")
    for i, item in enumerate(importance[:15], 1):
        bar = "#" * int(item['importance'] * 200)
        print(f"  {i:2}. {item['feature']:30s} {item['importance']:.4f}  {bar}")

    print(f"\n{'=' * 70}")
    print("RESULTAT FINAL")
    print(f"{'=' * 70}")
    print(f"Meilleur modele : {best_name}")
    print(f"AUC             : {best_metrics['auc']:.4f}")
    print(f"Precision       : {best_metrics['precision']:.3f}")
    print(f"Recall          : {best_metrics['recall']:.3f}")
    print(f"F1-score        : {best_metrics['f1']:.3f}")


if __name__ == '__main__':
    main()
