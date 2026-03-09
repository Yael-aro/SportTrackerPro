"""
SportTracker Pro - Service de Notifications
==========================================
Gestion des notifications par email pour alertes critiques
"""

from flask_mail import Mail, Message
from flask import current_app
from datetime import datetime
import logging

mail = Mail()
logger = logging.getLogger(__name__)


def send_injury_alert(user, player, injury):
    """Alerte quand une blessure est enregistrée"""
    subject = f"🏥 Alerte Blessure - {player.full_name}"
    
    body = f"""
Bonjour {user.first_name},

Une nouvelle blessure a été enregistrée :

📋 Détails :
- Joueur : {player.full_name}
- Type : {injury.injury_type}
- Zone : {injury.body_part}
- Date : {injury.date_injury.strftime('%d/%m/%Y')}
- Durée estimée : {injury.days_out} jours

⚠️ Statut : {'ACTIF' if injury.is_active else 'Guéri'}

Consultez le dashboard médical pour plus de détails :
http://localhost:8080/medical/injuries

---
SportTrackerPro - Système d'alertes médical
"""
    
    _send_email(user.email, subject, body)


def send_acwr_alert(user, team, acwr_data):
    """Alerte quand ACWR > 1.3 (warning) ou > 1.5 (danger)"""
    
    alert_level = "🔴 DANGER" if acwr_data['acwr'] > 1.5 else "🟠 ATTENTION"
    subject = f"{alert_level} - ACWR Élevé - {team.name}"
    
    body = f"""
Bonjour {user.first_name},

Plusieurs joueurs de l'équipe {team.name} présentent un ACWR élevé.

📊 Résumé :
- ACWR moyen : {acwr_data['acwr']:.2f}
- Joeurs à risque : {acwr_data['count']}
- Seuil critique : 1.5

⚠️ Recommandations :
- Réduire la charge d'entraînement
- Augmenter les jours de récupération
- Consulter les données GPS pour détails

Consultez le dashboard pour plus :
http://localhost:8080/dashboard/coach

---
SportTrackerPro - Système d'alertes de charge
"""
    
    _send_email(user.email, subject, body)


def send_wellness_alert(user, players_at_risk):
    """Alerte quand bien-être collectif est bas"""
    
    subject = f"⚠️ Alerte Bien-être - Score Bas"
    
    player_list = "\n".join([
        f"  • {p.full_name} - Score: {p.wellness_score}/25"
        for p in players_at_risk
    ])
    
    body = f"""
Bonjour {user.first_name},

Le bien-être de plusieurs joueurs est en baisse :

😟 Joueurs en alerte :
{player_list}

📋 Recommandations :
- Augmenter les séances de récupération
- Vérifier la qualité du sommeil
- Réduire le stress/charge
- Consulter l'équipe médicale si nécessaire

Consultez le dashboard :
http://localhost:8080/medical/wellness

---
SportTrackerPro - Système d'alertes bien-être
"""
    
    _send_email(user.email, subject, body)


def send_overload_alert(user, player, load_data):
    """Alerte surcharge énergétique"""
    
    subject = f"⚡ Surcharge Détectée - {player.full_name}"
    
    body = f"""
Bonjour {user.first_name},

Le joueur {player.full_name} montre des signes de surcharge :

📈 Métriques :
- Charge hebdo : {load_data['weekly']:.0f} AU
- Charge chronique : {load_data['chronic']:.0f} AU
- ACWR : {load_data['acwr']:.2f}
- TSB : {load_data['tsb']:.0f}

⚠️ Risque : Potentiel surtraining/blessure

Actions recommandées :
1. Réduire volume entraînement demain
2. Augmenter jours repos/récupération
3. Monitorer étroitement les 7 prochaines jours
4. Consultation médicale si persistance

Dashboard détaillé :
http://localhost:8080/players/{player.id}

---
SportTrackerPro - Système d'alertes de surcharge
"""
    
    _send_email(user.email, subject, body)


def _send_email(recipient, subject, body):
    """Fonction interne pour envoyer un email"""
    
    try:
        msg = Message(
            subject=subject,
            recipients=[recipient],
            body=body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@sporttrackerpro.com')
        )
        mail.send(msg)
        logger.info(f"✅ Email envoyé à {recipient}: {subject}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur email à {recipient}: {str(e)}")
        return False
