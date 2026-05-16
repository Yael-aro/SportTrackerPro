"""
RajaTracker - API REST
===========================
Endpoints API pour intégrations externes et graphiques
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from datetime import date, timedelta
from sqlalchemy import func
from app.models import db, Player, Team, TrainingSession, TrainingResult, GPSData, WellnessRecord

api_bp = Blueprint('api', __name__)


# =============================================================================
# API JOUEURS
# =============================================================================

@api_bp.route('/players')
@login_required
def get_players():
    """Liste des joueurs"""
    team_id = request.args.get('team_id', type=int)
    status = request.args.get('status')
    
    query = Player.query
    
    if team_id:
        query = query.filter_by(team_id=team_id)
    if status:
        query = query.filter_by(status=status)
    
    players = query.all()
    
    return jsonify([{
        'id': p.id,
        'name': p.full_name,
        'position': p.position,
        'status': p.status,
        'team': p.team.name if p.team else None,
        'age': p.age
    } for p in players])


@api_bp.route('/players/<int:id>/metrics')
@login_required
def get_player_metrics(id):
    """Métriques d'un joueur"""
    player = Player.query.get_or_404(id)
    
    return jsonify({
        'id': player.id,
        'name': player.full_name,
        'weekly_load': player.get_weekly_load(),
        'acwr': player.get_acwr(),
        'fitness': player.get_fitness(),
        'fatigue': player.get_fatigue(),
        'tsb': player.get_tsb(),
        'form_status': player.get_form_status()
    })


# =============================================================================
# API ÉQUIPES
# =============================================================================

@api_bp.route('/teams')
@login_required
def get_teams():
    """Liste des équipes"""
    teams = Team.query.all()
    
    return jsonify([{
        'id': t.id,
        'name': t.name,
        'category': t.category,
        'player_count': t.player_count,
        'available': t.available_players
    } for t in teams])


@api_bp.route('/teams/<int:id>/load')
@login_required
def get_team_load(id):
    """Charge d'équipe"""
    team = Team.query.get_or_404(id)
    
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    
    # Charge par jour
    daily_loads = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        
        total = db.session.query(
            func.sum(TrainingResult.training_load)
        ).join(TrainingSession).join(Player).filter(
            Player.team_id == id,
            TrainingSession.date == day
        ).scalar() or 0
        
        daily_loads.append({
            'date': day.isoformat(),
            'day': day.strftime('%a'),
            'load': round(total, 1)
        })
    
    return jsonify({
        'team_id': id,
        'team_name': team.name,
        'current_load': team.get_team_load(week_start),
        'target_load': team.target_weekly_load,
        'daily_loads': daily_loads
    })


# =============================================================================
# API GPS
# =============================================================================

@api_bp.route('/gps/session/<int:session_id>')
@login_required
def get_session_gps(session_id):
    """Données GPS d'une séance"""
    gps_data = GPSData.query.filter_by(session_id=session_id).all()
    
    return jsonify([{
        'player_id': g.player_id,
        'player_name': g.player.full_name if g.player else 'Unknown',
        'total_distance': g.total_distance,
        'hsr_distance': g.hsr_distance,
        'sprint_distance': g.sprint_distance,
        'max_speed': g.max_speed,
        'player_load': g.player_load,
        'hr_avg': g.hr_avg,
        'hr_max': g.hr_max
    } for g in gps_data])


@api_bp.route('/gps/player/<int:player_id>/history')
@login_required
def get_player_gps_history(player_id):
    """Historique GPS d'un joueur"""
    days = request.args.get('days', 30, type=int)
    
    since = date.today() - timedelta(days=days)
    
    gps_data = GPSData.query.filter(
        GPSData.player_id == player_id,
        GPSData.recorded_at >= since
    ).order_by(GPSData.recorded_at).all()
    
    return jsonify([{
        'date': g.recorded_at.isoformat(),
        'session_id': g.session_id,
        'total_distance': g.total_distance,
        'hsr_distance': g.hsr_distance,
        'player_load': g.player_load,
        'max_speed': g.max_speed
    } for g in gps_data])


# =============================================================================
# API DASHBOARD
# =============================================================================

@api_bp.route('/dashboard/summary')
@login_required
def get_dashboard_summary():
    """Résumé pour le dashboard"""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    
    return jsonify({
        'players': {
            'total': Player.query.count(),
            'available': Player.query.filter_by(status='Disponible').count(),
            'injured': Player.query.filter_by(status='Blessé').count(),
            'fatigued': Player.query.filter_by(status='Fatigué').count()
        },
        'sessions': {
            'this_week': TrainingSession.query.filter(
                TrainingSession.date >= week_start,
                TrainingSession.date < week_start + timedelta(days=7)
            ).count(),
            'completed': TrainingSession.query.filter(
                TrainingSession.date >= week_start,
                TrainingSession.is_completed == True
            ).count()
        },
        'teams': Team.query.count()
    })


@api_bp.route('/dashboard/alerts')
@login_required
def get_alerts():
    """Alertes actives"""
    alerts = []
    
    for player in Player.query.filter_by(status='Disponible').all():
        acwr = player.get_acwr()
        tsb = player.get_tsb()
        
        if acwr > 1.5:
            alerts.append({
                'type': 'danger',
                'player_id': player.id,
                'player_name': player.full_name,
                'message': f'ACWR critique: {acwr}',
                'metric': 'acwr',
                'value': acwr
            })
        elif acwr > 1.3:
            alerts.append({
                'type': 'warning',
                'player_id': player.id,
                'player_name': player.full_name,
                'message': f'ACWR élevé: {acwr}',
                'metric': 'acwr',
                'value': acwr
            })
        
        if tsb < -20:
            alerts.append({
                'type': 'danger',
                'player_id': player.id,
                'player_name': player.full_name,
                'message': f'TSB très bas: {tsb}',
                'metric': 'tsb',
                'value': tsb
            })
    
    # Trier par gravité
    alerts.sort(key=lambda x: (0 if x['type'] == 'danger' else 1, -abs(x['value'])))
    
    return jsonify(alerts[:10])


@api_bp.route('/dashboard/weekly-load')
@login_required
def get_weekly_load_chart():
    """Données de charge pour graphique"""
    team_id = request.args.get('team_id', type=int)
    
    today = date.today()
    data = []
    
    for i in range(7):
        day = today - timedelta(days=6-i)
        
        query = db.session.query(
            func.avg(TrainingResult.training_load).label('avg_load'),
            func.sum(TrainingResult.training_load).label('total_load'),
            func.count(TrainingResult.id).label('count')
        ).join(TrainingSession).filter(
            TrainingSession.date == day
        )
        
        if team_id:
            query = query.join(Player).filter(Player.team_id == team_id)
        
        result = query.first()
        
        data.append({
            'date': day.strftime('%a %d'),
            'avg_load': round(result.avg_load or 0, 1),
            'total_load': round(result.total_load or 0, 1),
            'sessions': result.count or 0
        })
    
    return jsonify(data)


# =============================================================================
# API WELLNESS
# =============================================================================

@api_bp.route('/wellness/today')
@login_required
def get_wellness_today():
    """Wellness d'aujourd'hui"""
    today = date.today()
    
    records = WellnessRecord.query.filter_by(date=today).all()
    
    return jsonify([{
        'player_id': r.player_id,
        'player_name': r.player.full_name if r.player else 'Unknown',
        'total_score': r.total_score,
        'fatigue': r.fatigue,
        'sleep_quality': r.sleep_quality,
        'muscle_soreness': r.muscle_soreness,
        'status': r.wellness_status
    } for r in records])
