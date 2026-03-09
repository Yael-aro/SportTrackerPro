# 📦 SportTrackerPro - Guide Complet v2.0

## 🆕 Améliorations Récentes

### **Nouvelles Fonctionnalités (2026)**

✨ **Notifications Email** - Alertes automatiques pour ACWR, blessures, bien-être  
📄 **Export PDF** - Rapports complets joueur et équipe  

---

## 🚀 Installation Rapide

### 1. Clone & Setup
```bash
cd /path/to/SportTrackerPro
python -m venv .venv
source .venv/bin/activate  # ou .venv\Scripts\activate sur Windows
pip install -r requirements.txt
```

### 2. Configuration Email (optionnel mais recommandé)

Créer un fichier `.env` :

```bash
# Email Configuration (Gmail)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=votre_email@gmail.com
MAIL_PASSWORD=votre_app_password
MAIL_DEFAULT_SENDER=noreply@sporttrackerpro.com

# Autres configs optionnelles
FLASK_ENV=development
SECRET_KEY=your_secret_key_here
```

**Pour Gmail :**
1. Aller sur https://myaccount.google.com/apppasswords
2. Générer une "App Password"
3. Utiliser cette password dans MAIL_PASSWORD

### 3. Base de Données

```bash
export FLASK_APP=run.py
flask init-db        # Initialiser avec données de test
python run.py        # Lancer l'app sur http://localhost:8080
```

---

## 👥 Comptes de Test

### Staff (mot de passe requis)
```
Email: admin@sporttracker.com        Password: admin123
Email: coach@sporttracker.com        Password: coach123
```

### Joueurs (pas de mot de passe)
Format: `prenom.nom@sporttracker.com`

- youssef.elamrani@sporttracker.com
- karim.benali@sporttracker.com
- omar.tazi@sporttracker.com
- mehdi.alaoui@sporttracker.com
- amine.rachidi@sporttracker.com
- hamza.idrissi@sporttracker.com
- said.moussaoui@sporttracker.com
- ayoub.mansouri@sporttracker.com
- bilal.chakir@sporttracker.com
- reda.fikri@sporttracker.com
- soufiane.berrada@sporttracker.com
- adam.ouazzani@sporttracker.com
- zakaria.lamrani@sporttracker.com
- othmane.hajji@sporttracker.com

---

## 🔔 Notifications par Email

### Comment Ça Marche

Quand un événement critique se produit, un email est automatiquement envoyé aux utilisateurs pertinents :

| Événement | Destinataire | Condition |
|-----------|---|---|
| **Nouvelle Blessure** | Coach + Médecin | Blessure enregistrée |
| **ACWR Élevé** | Coach | ACWR > 1.3 (attention) / > 1.5 (danger) |
| **Bien-être Bas** | Médecin | Score < 10 |
| **Surcharge** | Coach | Multiple d'indicateurs high-risk |

### Exemple Email

```
🏥 Alerte Blessure - Youssef El Amrani

Une nouvelle blessure a été enregistrée :

📋 Détails :
- Joueur : Youssef El Amrani
- Type : Déchirure
- Zone : Quadriceps
- Date : 09/03/2026
- Durée estimée : 14 jours

⚠️ Statut : ACTIF

Consultez le dashboard médical pour plus de détails.
```

### Tracer les Emails (Dev Mode)

Pour voir les emails en développement sans configurer SMTP :

```python
# app/__init__.py
if app.config['TESTING_MAIL']:
    app.logger.info(f"Email envoyé à: {msg.recipients}")
    # Dans les logs Flask
```

---

## 📄 Export PDF

### Utilisation

Trois options pour exporter :

#### 1. Rapport Joueur
```
GET /exports/player/5/pdf
```
**Inclut :**
- Infos personnelles + équipe + poste
- Toutes les métriques actuelles (ACWR, TSB, Charge, Fitness)
- Historique des 10 dernières blessures
- Bien-être des 30 derniers jours

**Permissions :** Coach, Médecin, Analyste, Admin,  + le joueur lui-même

#### 2. Rapport Équipe
```
GET /exports/team/2/pdf
```
**Inclut :**
- Infos équipe + catégorie
- Nombres joueurs (total, disponible, blessés)
- Métriques agrégées (ACWR moyen, TSB moyen, Charge)

**Permissions :** Coach, Analyste, Dirigeant, Admin

#### 3. Résumé Saisonnier
```
GET /exports/seasonal-summary
```

Retourne JSON avec tous les joueurs et leurs métriques actuelles.

### Exemple - Générer Rapport

```bash
# Télécharge automatiquement
curl http://localhost:8080/exports/player/5/pdf -o rapport.pdf

# Via navigateur
http://localhost:8080/exports/player/5/pdf
```

### Intégration Frontend

Ajouter les liens dans un template :

```html
<!-- Bouton Télécharger -->
<a href="/exports/player/{{ player.id }}/pdf" 
   class="btn btn-sm btn-info" 
   download>
    <i class="bi bi-file-pdf"></i> Télécharger PDF
</a>
```

---

## 📊 Fichier Structure

```
SportTrackerPro/
├── app/
│   ├── services/              # ✨ NEW: Services utils
│   │   ├── notifications.py   # Email alerts
│   │   ├── pdf_export.py      # PDF generation
│   │   └── __init__.py
│   ├── routes/
│   │   ├── exports.py         # ✨ NEW: Export routes
│   │   ├── auth.py
│   │   ├── players.py
│   │   ├── medical.py
│   │   └── ... (autres routes)
│   ├── models.py
│   ├── forms.py
│   └── __init__.py
├── config.py                  # ✨ UPDATED: Email config
├── run.py
├── requirements.txt           # ✨ UPDATED: New packages
└── DEPLOYMENT.md
```

---

## ⚙️ Configuration Avancée

### Variables Environnement

```bash
# Flask
FLASK_ENV=development              # ou 'production'
FLASK_APP=run.py
SECRET_KEY=your_secret_key

# Database
DATABASE_URL=sqlite:///sporttracker.db     # ou PostgreSQL

# Email
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
MAIL_DEFAULT_SENDER=noreply@sporttrackerpro.com
TESTING_MAIL=False

# GPS Upload
MAX_GPS_FILE_SIZE=50MB
GPS_UPLOAD_FOLDER=/path/uploads/gps
```

### Email Production

Pour deployer en production, utiliser one of:

1. **Gmail (simple)**
   - Générer App Password
   - Mettre dans MAIL_PASSWORD

2. **SendGrid**
   ```python
   # config.py
   MAIL_SERVER='smtp.sendgrid.net'
   MAIL_PORT=587
   MAIL_USERNAME='apikey'
   MAIL_PASSWORD='SG.key...'
   ```

3. **AWS SES**
   ```python
   MAIL_SERVER='email-smtp.region.amazonaws.com'
   MAIL_PORT=587
   ```

---

## 🧪 Testing

### Tests Email

```python
# Test envoyer email
from app.services import notifications
from app.models import User, Player

user = User.query.first()
player = Player.query.first()

notifications.send_injury_alert(user, player, injury_obj)
```

### Tests PDF

```bash
# Télécharger rapport joueur
curl http://localhost:8080/exports/player/1/pdf -o test.pdf

# Vérifier fichier
file test.pdf     # Should be: PDF document
```

---

## 🔐 Permissions Détaillées

### Export PDF

| Rôle | Joueur | Équipe | Résumé Saison |
|------|--------|--------|---|
| Admin | ✅ | ✅ | ✅ |
| Coach | ✅* | ✅* | ✅ |
| Médecin | ✅ | ✅ | ✅ |
| Analyste | ✅ | ✅ | ✅ |
| Dirigeant | ✅ |  ✅ | ✅ |
| Préparateur | ✅* | ✅* | ❌ |
| Joueur | ✅** | ❌ | ❌ |

\* = Seulement leurs données  
\*\* = Seulement propre rapport

### Notifications Email

| Événement | Admin | Coach | Médecin | Analyste |
|-----------|-------|-------|---------|----------|
| Blessure | ✅ | ✅ | ✅ | ❌ |
| ACWR > 1.3 | ✅ | ✅ | ✅ | ❌ |
| Bien-être < 10 | ✅ | ❌ | ✅ | ❌ |
| Surcharge | ✅ | ✅ | ✅ | ❌ |

---

## 🐛 Troubleshooting

### Email ne s'envoie pas

```python
# Vérifier config
flask shell
>>> from app import app, mail
>>> app.config['MAIL_SERVER']  # Doit être 'smtp.gmail.com'
>>> app.config['MAIL_USERNAME']  # Doit être rempli

# Test d'envoi
>>> from flask_mail import Message
>>> msg = Message('Test', recipients=['your_email@gmail.com'])
>>> mail.send(msg)
```

### Gmail App Password

1. Aller sur: https://myaccount.google.com/apppasswords
2. Sélectionner "Mail" et "Windows Computer"
3. Générer le password
4. Copier/coller dans MAIL_PASSWORD

### PDF generation error

```
ERROR: reportlab not installed
SOLUTION: pip install reportlab PyPDF2
```

### Port 8080 Already in Use

```bash
# Trouver le processus
lsof -i :8080

# Tuer le processus
kill -9 <PID>

# Ou changer port in run.py
app.run(port=8000)
```

---

## 📚 Documentation Supplémentaire

- **API Endpoints** → `/api/*` routes (voir api.py)
- **Database Schema** → Voir `app/models.py`
- **Formes** → Voir `app/forms.py`
- **Templates** → Voir `app/templates/`

---

## 🎯 Checklist Livraison

- [x] Core features implémentées
- [x] Multi-rôles avec RBAC
- [x] Notifications email
- [x] Export PDF
- [x] API REST
- [x] Données de test pré-chargées
- [x] Documentation complète
- [ ] Tests unitaires (À faire)
- [ ] Modèles ML (Phase 2)

---

## 📞 Support

Pour toute question :
1. Consulter la documentation
2. Vérifier les logs : `flask run --reload`
3. Tester en dev mode avec TESTING_MAIL=True
4. Vérifier la DB : `flask shell`

---

**Version :** 2.0  
**Dernière mise à jour :** 9 Mars 2026  
**Status :** ✅ Production-Ready (core features)
