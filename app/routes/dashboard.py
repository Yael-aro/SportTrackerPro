"""
SportTracker Pro - Routes Dashboard
===================================
Tableaux de bord personnalisés par rôle
"""

from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from datetime import date, timedelta
from sqlalchemy import func
from app.ml.predict import predict_from_player_db
from app.ml.explain import explain_prediction
from app.models import db, Player, Team, TrainingSession, TrainingResult, GPSData, Injury, WellnessRecord, Recommendation

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    """Dashboard principal - Redirige vers le bon dashboard"""
    role = current_user.role
    
    if role in ['coach', 'assistant']:
        return coach_dashboard()
    elif role == 'preparateur':
        return preparateur_dashboard()
    elif role == 'admin':
        return admin_dashboard()
    elif role == 'analyst':
        return analyst_dashboard()
    elif role == 'dirigeant':
        return dirigeant_dashboard()
    else:
        return coach_dashboard()


@dashboard_bp.route('/coach')
@login_required
def coach():
    """Dashboard Entraîneur"""
    return coach_dashboard()


def coach_dashboard():
    """Génère le dashboard entraîneur"""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    
    # Statistiques globales
    stats = {
        'total_players': Player.query.count(),
        'available_players': Player.query.filter_by(status='Disponible').count(),
        'injured_players': Player.query.filter_by(status='Blessé').count(),
        'fatigued_players': Player.query.filter_by(status='Fatigué').count(),
        'total_teams': Team.query.count(),
        'sessions_this_week': TrainingSession.query.filter(
            TrainingSession.date >= week_start,
            TrainingSession.date <= today + timedelta(days=7-today.weekday())
        ).count(),
        'sessions_completed': TrainingSession.query.filter(
            TrainingSession.date >= week_start,
            TrainingSession.is_completed == True
        ).count()
    }
    
    # Prochaines séances (7 prochains jours)
    upcoming_sessions = TrainingSession.query.filter(
        TrainingSession.date >= today,
        TrainingSession.date <= today + timedelta(days=7)
    ).order_by(TrainingSession.date, TrainingSession.start_time).limit(5).all()
    
    # Joueurs à risque (ACWR > 1.3 ou wellness faible)
    players_at_risk = []
    for player in Player.query.filter_by(status='Disponible').all():
        acwr = player.get_acwr()
        tsb = player.get_tsb()
        
        if acwr > 1.3 or tsb < -10:
            players_at_risk.append({
                'player': player,
                'acwr': acwr,
                'tsb': tsb,
                'status': player.get_form_status()
            })
    
    # Trier par risque
    players_at_risk.sort(key=lambda x: (x['acwr'], -x['tsb']), reverse=True)
    players_at_risk = players_at_risk[:5]
    

    # Predictions IA (Random Forest, AUC 0.685)
    players_ai_risk = []
    for player in Player.query.filter(Player.status != 'Blesse').all():
        try:
            prediction = predict_from_player_db(player)
            players_ai_risk.append({
                'player': player,
                'risk_percent': prediction['risk_percent'],
                'risk_level': prediction['risk_level'],
                'risk_color': prediction['risk_color'],
                'risk_score': prediction['risk_score'],
            })
        except Exception as e:
            # En cas d'erreur, on ignore ce joueur
            continue

    # Trier par risque decroissant, garder le top 10
    players_ai_risk.sort(key=lambda x: x['risk_score'], reverse=True)
    players_ai_risk = players_ai_risk[:10]

    # Charge d'équipe
    team_loads = []
    for team in Team.query.all():
        load = team.get_team_load(week_start)
        team_loads.append({
            'team': team,
            'load': round(load, 1),
            'target': team.target_weekly_load,
            'percentage': round((load / team.target_weekly_load * 100) if team.target_weekly_load else 0)
        })
    
    # Données pour les graphiques
    chart_data = {
        'player_status': {
            'labels': ['Disponibles', 'Blessés', 'Fatigués', 'En récupération'],
            'data': [
                stats['available_players'],
                stats['injured_players'],
                stats['fatigued_players'],
                Player.query.filter_by(status='En récupération').count()
            ],
            'colors': ['#27ae60', '#e74c3c', '#f39c12', '#3498db']
        }
    }
    
    # Recommandations actives
    recommendations = Recommendation.query.filter_by(
        is_actioned=False
    ).order_by(
        Recommendation.priority.desc(),
        Recommendation.created_at.desc()
    ).limit(5).all()
    
    return render_template('dashboard/coach.html',
                          stats=stats,
                          upcoming_sessions=upcoming_sessions,
                          players_at_risk=players_at_risk,
                          players_ai_risk=players_ai_risk,
                          team_loads=team_loads,
                          chart_data=chart_data,
                          recommendations=recommendations)


@dashboard_bp.route('/preparateur')
@login_required
def preparateur():
    """Dashboard Préparateur Physique"""
    return preparateur_dashboard()


def preparateur_dashboard():
    """Génère le dashboard préparateur physique"""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    
    # Métriques GPS de la semaine
    gps_stats = db.session.query(
        func.avg(GPSData.total_distance).label('avg_distance'),
        func.avg(GPSData.player_load).label('avg_load'),
        func.avg(GPSData.hsr_distance).label('avg_hsr'),
        func.max(GPSData.max_speed).label('max_speed')
    ).join(TrainingSession).filter(
        TrainingSession.date >= week_start
    ).first()
    
    # Top 5 joueurs par charge
    top_players_load = []
    for player in Player.query.filter_by(status='Disponible').all():
        weekly_load = player.get_weekly_load(week_start)
        if weekly_load > 0:
            top_players_load.append({
                'player': player,
                'load': round(weekly_load, 1),
                'acwr': player.get_acwr()
            })
    
    top_players_load.sort(key=lambda x: x['load'], reverse=True)
    top_players_load = top_players_load[:10]
    
    # Alertes ACWR
    acwr_alerts = []
    for player in Player.query.filter_by(status='Disponible').all():
        acwr = player.get_acwr()
        if acwr > 1.3:
            acwr_alerts.append({
                'player': player,
                'acwr': acwr,
                'level': 'danger' if acwr > 1.5 else 'warning'
            })
    
    acwr_alerts.sort(key=lambda x: x['acwr'], reverse=True)
    
    return render_template('dashboard/preparateur.html',
                          gps_stats=gps_stats,
                          top_players_load=top_players_load,
                          acwr_alerts=acwr_alerts)


@dashboard_bp.route('/admin')
@login_required
def admin():
    """Dashboard Administrateur"""
    return admin_dashboard()


def admin_dashboard():
    """Génère le dashboard administrateur"""
    from app.models import User
    
    stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'total_players': Player.query.count(),
        'total_teams': Team.query.count(),
        'total_sessions': TrainingSession.query.count(),
        'gps_records': GPSData.query.count()
    }
    
    # Utilisateurs par rôle
    users_by_role = db.session.query(
        User.role,
        func.count(User.id)
    ).group_by(User.role).all()
    
    return render_template('dashboard/admin.html',
                          stats=stats,
                          users_by_role=users_by_role)


def analyst_dashboard():
    """Dashboard Analyste"""
    return render_template('dashboard/analyst.html')


def dirigeant_dashboard():
    """Dashboard Dirigeant"""
    stats = {
        'total_players': Player.query.count(),
        'total_teams': Team.query.count(),
        'injured_count': Player.query.filter_by(status='Blessé').count(),
        'sessions_month': TrainingSession.query.filter(
            TrainingSession.date >= date.today().replace(day=1)
        ).count()
    }
    
    return render_template('dashboard/dirigeant.html', stats=stats)


# =============================================================================
# API ENDPOINTS POUR LES GRAPHIQUES
# =============================================================================

@dashboard_bp.route('/api/weekly-load')
@login_required
def api_weekly_load():
    """Données de charge hebdomadaire pour Chart.js"""
    team_id = request.args.get('team_id', type=int)
    
    data = []
    today = date.today()
    
    for i in range(7):
        day = today - timedelta(days=6-i)
        
        query = db.session.query(
            func.sum(TrainingResult.training_load)
        ).join(TrainingSession).filter(
            TrainingSession.date == day
        )
        
        if team_id:
            query = query.filter(TrainingSession.team_id == team_id)
        
        total = query.scalar() or 0
        
        data.append({
            'date': day.strftime('%a %d'),
            'load': round(total, 1)
        })
    
    return jsonify(data)


@dashboard_bp.route('/api/player-status')
@login_required
def api_player_status():
    """Répartition des joueurs par statut"""
    statuses = db.session.query(
        Player.status,
        func.count(Player.id)
    ).group_by(Player.status).all()
    
    return jsonify([
        {'status': s[0], 'count': s[1]} for s in statuses
    ])
