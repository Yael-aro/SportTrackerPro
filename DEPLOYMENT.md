# 📦 Guide de Déploiement - SportTrackerPro

## 🚀 Mise en Route Rapide

### 1. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

### 2. **Initialiser la base de données**
```bash
export FLASK_APP=run.py
flask init-db
```

Cela crée automatiquement :
- Les tables de la base de données
- 3 équipes (Seniors A, U19, U17)
- 14 joueurs de test
- 2 comptes staff

### 3. **Lancer l'application**
```bash
python run.py
```

L'app démarre sur : **http://localhost:8080**

---

## 👥 Comptes de Test Disponibles

### **👨‍💼 Staff (avec mot de passe)**

| Rôle | Email | Mot de passe |
|------|-------|------------|
| **Admin** | admin@sporttracker.com | `admin123` |
| **Coach** | coach@sporttracker.com | `coach123` |

### **⚽ Joueurs (sans mot de passe)**

Sélectionnez le rôle **"Joueur"** et utilisez : `prenom.nom@sporttracker.com`

#### Seniors A
- youssef.elamrani@sporttracker.com
- karim.benali@sporttracker.com
- omar.tazi@sporttracker.com
- mehdi.alaoui@sporttracker.com
- amine.rachidi@sporttracker.com
- hamza.idrissi@sporttracker.com
- said.moussaoui@sporttracker.com

#### U19
- ayoub.mansouri@sporttracker.com
- bilal.chakir@sporttracker.com
- reda.fikri@sporttracker.com
- soufiane.berrada@sporttracker.com

#### U17
- adam.ouazzani@sporttracker.com
- zakaria.lamrani@sporttracker.com
- othmane.hajji@sporttracker.com

---

## 🔑 Créer Nouveaux Comptes Staff

### **Via l'interface web**
1. Allez sur : http://localhost:8080/auth/register
2. Remplissez le formulaire avec les rôles disponibles :
   - Entraîneur
   - Entraîneur Adjoint
   - Préparateur Physique
   - Staff Médical
   - Analyste
   - Dirigeant

**Note :** Les comptes Admin ne peuvent être créés que via manipulation directe de la base de données.

---

## 🔄 Réinitialiser la Base de Données

Pour effacer toutes les données et recommencer :
```bash
export FLASK_APP=run.py
flask reset-db
flask init-db
```

---

## 📋 Rôles et Permissions Implémentés

| Rôle | Permissions |
|------|------------|
| **Coach** | Gestion des joueurs, séances, résultats, GPS, tableau de bord |
| **Entraîneur Adjoint** | Lecture joueurs, séances, résultats, tableau de bord |
| **Préparateur** | Gestion séances, GPS, résultats, ML, tableau de bord |
| **Médecin** | Gestion médicale, blessures, bien-être, tableau de bord |
| **Analyste** | Analyse GPS, résultats, rapports, tableau de bord |
| **Dirigeant** | Rapports généraux, synthèses, tableau de bord |
| **Joueur** | Profil personnel, stats, schedules, bien-être |
| **Admin** | Accès complet, gestion des utilisateurs |

---

## ✅ Fonctionnalités Implémentées

✅ **Authentification Multi-Rôles**
- Login simplifié pour joueurs
- Login sécurisé pour staff
- Auto-création de compte joueur au premier login
- Inscription de nouveaux comptes staff

✅ **Gestion des Joueurs**
- Profil détaillé (info personnelles, metrics)
- Historique blessures
- Suivi bien-être (wellness tracking)
- Upload de photos

✅ **Gestion des Équipes**
- Organisation par catégorie
- Liaison avec joueurs

✅ **Tableaux de Bord**
- Dashboard personnalisé par rôle
- Métriques ACWR, TSB, État de forme

---

## 🛠️ Commandes Utiles

```bash
# Initialiser DB avec données de test
flask init-db

# Réinitialiser complètement
flask reset-db

# Lancer l'app
python run.py

# Activer l'environnement virtuel (si besoin)
source .venv/bin/activate
```

---

## ⚙️ Configuration

### Variables d'Environnement
```bash
export FLASK_APP=run.py
export FLASK_ENV=development
export SECRET_KEY=votre_clé_secrète
```

### Fichiers Clés
- `config.py` - Configuration générale  
- `run.py` - Point d'entrée  
- `app/models.py` - Modèles de données  
- `app/forms.py` - Formulaires  
- `app/routes/` - Endpoints  

---

## 🐛 Troubleshooting

### Erreur : "flask: command not found"
```bash
source .venv/bin/activate
```

### Erreur : "Database already exists"
```bash
flask reset-db
flask init-db
```

### Port 8080 en cours d'utilisation
Modifier le port dans `run.py` :
```python
app.run(debug=True, host='0.0.0.0', port=8000)
```

---

## 📊 Structure du Projet

```
SportTrackerPro/
├── app/
│   ├── routes/              # Endpoints (auth, players, coaches, etc.)
│   ├── templates/           # Templates HTML
│   ├── static/              # CSS, JS, images
│   ├── __init__.py          # Initialisation Flask + setup DB
│   ├── models.py            # Modèles SQLAlchemy
│   └── forms.py             # Formulaires WTForms
├── config.py                # Configuration
├── run.py                   # Main entry point
├── requirements.txt         # Dépendances
└── DEPLOYMENT.md            # Ce fichier
```

---

## 🧪 Tests Recommandés

1. **Test de Login**
   - Admin → admin@sporttracker.com / admin123
   - Coach → coach@sporttracker.com / coach123
   - Joueur → youssef.elamrani@sporttracker.com (no password)

2. **Inscription Staff**
   - Aller sur /auth/register
   - Créer un nouveau coach

3. **Navigation Modules**
   - Vérifier les dashboards par rôle
   - Consulter les pages joueurs, équipes

4. **Fonctionnalités**
   - Upload GPS
   - Éditer profil joueur
   - Ajouter blessure/wellness

---

## 📝 Checklist Livraison

- [x] Base de données fonctionnelle
- [x] Authentification multi-rôles
- [x] Inscription staff disponible
- [x] Données de test pré-chargées
- [x] Dropdowns rôles harmonisés
- [x] Templates login/register stylisés
- [x] Tableaux de bord par rôle

---

**Version :** 2.0  
**Date :** 09 Mars 2026  
**Prêt pour déploiement :** ✅ OUI
