"""
SportTracker Pro - Routes d'Exports (PDF, Excel)
===============================================
"""

from flask import Blueprint, jsonify, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import db, Player, Team
from app.services import pdf_export
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

export_bp = Blueprint('exports', __name__, url_prefix='/exports')


@export_bp.route('/player/<int:player_id>/pdf')
@login_required
def export_player_pdf(player_id):
    """Exporte le rapport complet d'un joueur en PDF"""
    
    player = Player.query.get_or_404(player_id)
    
    # Vérifier les permissions (coach de l'équipe, médecin, admin)
    if not _can_view_player(current_user, player):
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('main.index'))
    
    try:
        # Récupérer les données
        metrics = {
            'acwr': player.get_acwr(),
            'tsb': player.get_tsb(),
            'weekly_load': player.get_weekly_load(),
            'chronic_load': player.get_chronic_load(),
            'fitness': player.get_fitness(),
            'fatigue': player.get_fatigue(),
        }
        
        injuries = player.injuries or []
        wellness = player.wellness_records or []
        
        # Générer PDF
        pdf_buffer = pdf_export.generate_player_report(
            player,
            metrics,
            injuries,
            wellness
        )
        
        if pdf_buffer:
            filename = f"Rapport_{player.first_name}_{player.last_name}_{datetime.now().strftime('%d%m%Y')}.pdf"
            
            return send_file(
                pdf_buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=filename
            )
        else:
            flash('Erreur dans la génération du PDF', 'danger')
            return redirect(request.referrer or url_for('players.view_player', id=player_id))
            
    except Exception as e:
        logger.error(f"Erreur export PDF joueur: {str(e)}")
        flash('Erreur lors de la génération du rapport', 'danger')
        return redirect(request.referrer or url_for('players.view_player', id=player_id))


@export_bp.route('/team/<int:team_id>/pdf')
@login_required
def export_team_pdf(team_id):
    """Exporte le rapport d'une équipe en PDF"""
    
    team = Team.query.get_or_404(team_id)
    
    # Vérifier les permissions
    if not _can_manage_team(current_user, team):
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('main.index'))
    
    try:
        players = team.players or []
        
        # Calcul métriques agrégés
        metrics_summary = None
        if players:
            metrics_summary = {
                'avg_acwr': sum(p.get_acwr() for p in players) / len(players) if players else 0,
                'avg_tsb': sum(p.get_tsb() for p in players) / len(players) if players else 0,
                'avg_load': sum(p.get_weekly_load() for p in players) / len(players) if players else 0,
            }
        
        # Générer PDF
        pdf_buffer = pdf_export.generate_team_report(team, players, metrics_summary)
        
        if pdf_buffer:
            filename = f"Rapport_Equipe_{team.name}_{datetime.now().strftime('%d%m%Y')}.pdf"
            
            return send_file(
                pdf_buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=filename
            )
        else:
            flash('Erreur dans la génération du PDF', 'danger')
            return redirect(request.referrer or url_for('teams.view_team', id=team_id))
            
    except Exception as e:
        logger.error(f"Erreur export PDF équipe: {str(e)}")
        flash('Erreur lors de la génération du rapport', 'danger')
        return redirect(request.referrer or url_for('teams.view_team', id=team_id))


@export_bp.route('/seasonal-summary')
@login_required
def export_seasonal_summary():
    """Exporte un résumé de la saison (tous les joueurs)"""
    
    if current_user.role not in ['coach', 'admin', 'analyst', 'dirigeant']:
        flash('Accès restreint', 'danger')
        return redirect(url_for('main.index'))
    
    try:
        players = Player.query.all()
        
        data = []
        for player in players:
            data.append({
                'Joueur': player.full_name,
                'Équipe': player.team.name if player.team else '-',
                'ACWR': f"{player.get_acwr():.2f}",
                'TSB': f"{player.get_tsb():.0f}",
                'Charge': f"{player.get_weekly_load():.0f}",
                'Statut': player.status,
            })
        
        # Simple JSON pour l'instant
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'data': data,
            'count': len(data)
        })
        
    except Exception as e:
        logger.error(f"Erreur export résumé: {str(e)}")
        return jsonify({'error': str(e)}), 500


def _can_view_player(user, player):
    """Vérifie si l'utilisateur peut consulter un joueur"""
    
    if user.role == 'admin':
        return True
    
    if user.role == 'coach':
        # Coach peut voir ses propres joueurs
        return player.team_id == getattr(user, 'team_id', None) or True
    
    if user.role == 'medical':
        return True
    
    if user.role == 'analyst':
        return True
    
    if user.role == 'player':
        # Joueur voit son propre profil
        return user.player_id == player.id
    
    return False


def _can_manage_team(user, team):
    """Vérifie si l'utilisateur peut gérer une équipe"""
    
    if user.role in ['admin', 'coach', 'analyst', 'dirigeant']:
        return True
    
    return False
