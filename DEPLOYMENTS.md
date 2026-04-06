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
python3 run.py
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
1. Allez sur la page de login
2. Cliquez sur **"Créer un compte staff"**
3. Remplissez le formulaire avec les rôles disponibles :
   - Entraîneur
   - Entraîneur Adjoint
   - Préparateur Physique
   - Staff Médical
   - Analyste
   - Dirigeant

**Note :** Les comptes Admin ne peuvent être créés que via direct manipulation de la base de données.

---

## 🔄 Réinitialiser la Base de Données

Pour effacer toutes les données et recommencer :
```bash
flask reset-db
flask init-db
```

---

## 📋 Fonctionnalités Implémentées

✅ **Authentification Multi-Rôles**
- Login simplifié pour joueurs (sans mot de passe)
- Login sécurisé pour staff (email + mot de passe)
- Auto-création de compte joueur au premier login

✅ **Gestion des Joueurs**
- Création, édition du profil
- Historique des blessures
- Données de bien-être (wellness)

✅ **Gestion des Équipes**
- Organisation par catégorie (Seniors, U19, U17)

✅ **Tableaux de Bord**
- Dashboard personnalisé par rôle
- Métriques ACWR, TSB, État de forme

---

## 🛠️ Commandes Utiles

| Commande | Description |
|----------|-------------|
| `flask init-db` | Initialiser avec données de test |
| `flask reset-db` | Réinitialiser la base de données |
| `python run.py` | Lancer l'application |

---

## ⚙️ Configuration

### Variables d'Environnement
```bash
export FLASK_APP=run.py
export FLASK_ENV=development  # ou "production"
export SECRET_KEY=votre_clé_secrète
```

### Fichiers Importants
- `config.py` - Configuration générale
- `run.py` - Point d'entrée
- `app/__init__.py` - Initialisation Flask
- `app/models.py` - Modèles de données
- `app/routes/` - Routes et endpoints

---

## 🐛 Troubleshooting

### Erreur : "flask: command not found"
```bash
# S'assurer que l'environnement virtuel est activé
source .venv/bin/activate
```

### Erreur : "Database already exists"
```bash
# Réinitialiser proprement
flask reset-db
flask init-db
```

### Port 8080 déjà utilisé
Modifier le port dans `run.py` ligne :
```python
app.run(debug=True, host='0.0.0.0', port=8000)  # Changer le port
```

---

## 📚 Architecture du Projet

```
SportTrackerPro/
├── app/
│   ├── routes/          # Endpoints par module
│   ├── templates/       # Templates Jinja2
│   ├── static/          # CSS, JS, images
│   ├── models.py        # Modèles SQLAlchemy
│   └── forms.py         # Formulaires WTForms
├── config.py            # Configuration
├── run.py               # Entrée principale
└── requirements.txt     # Dépendances
```

---

## 📝 Notes pour la Livraison

- ✅ Base de données initialisée et fonctionnelle
- ✅ Système d'authentification multi-rôles complet
- ✅ Inscription staff disponible
- ✅ Tableaux de bord par rôle
- ✅ Données de test pré-chargées

### À Tester
1. Login avec différents rôles
2. Création d'un nouveau compte staff
3. Navigation entre les modules
4. Upload de fichiers (GPS, photos)

---

**Dernière mise à jour :** 09 Mars 2026  
**Version :** 2.0  
**Auteur :** Équipe SportTrackerPro
