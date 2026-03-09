"""
SportTracker Pro - Portail Joueur
=================================
Interface dédiée aux joueurs
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from datetime import date, timedelta
from app.models import db, Player, TrainingSession, TrainingResult, GPSData, WellnessRecord, Recommendation
from app.forms import WellnessForm

player_portal_bp = Blueprint('player_portal', __name__)


def get_current_player():
    """Récupère le joueur connecté"""
    player_id = session.get('player_id')
    if player_id:
        return Player.query.get(player_id)
    if current_user.is_authenticated and current_user.player_id:
        return Player.query.get(current_user.player_id)
    return None


@player_portal_bp.route('/profile')
@login_required
def profile():
    """Profil du joueur"""
    player = get_current_player()
    if not player:
        return redirect(url_for('auth.login'))
    
    # Statistiques carrière
    total_sessions = TrainingResult.query.filter_by(player_id=player.id).count()
    total_distance = db.session.query(db.func.sum(GPSData.total_distance)).filter_by(
        player_id=player.id
    ).scalar() or 0
    
    best_distance = db.session.query(db.func.max(GPSData.total_distance)).filter_by(
        player_id=player.id
    ).scalar() or 0
    
    best_speed = db.session.query(db.func.max(GPSData.max_speed)).filter_by(
        player_id=player.id
    ).scalar() or 0
    
    # Calculer la précision (assiduité)
    accuracy = 100
    if total_sessions > 0:
        total_attendance = TrainingResult.query.filter_by(player_id=player.id, status='Completed').count()
        accuracy = round((total_attendance / total_sessions) * 100)
    
    # Derniers enregistrements wellness et injuries
    last_wellness = WellnessRecord.query.filter_by(player_id=player.id).order_by(
        WellnessRecord.created_at.desc()
    ).first()
    
    from app.models import Injury
    recent_injuries = Injury.query.filter_by(player_id=player.id).order_by(
        Injury.created_at.desc()
    ).limit(5).all()
    
    last_injury = recent_injuries[0] if recent_injuries else None
    
    stats = {
        'total_sessions': total_sessions,
        'total_distance': round(total_distance / 1000, 1) if total_distance else 0,  # en km
        'best_distance': round(best_distance, 0) if best_distance else 0,
        'best_speed': round(best_speed, 1) if best_speed else 0,
        'accuracy': accuracy
    }
    
    return render_template('player/profile.html', player=player, stats=stats, last_wellness=last_wellness, last_injury=last_injury, recent_injuries=recent_injuries)


@player_portal_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard du joueur"""
    player = get_current_player()
    if not player:
        flash('Profil joueur non trouvé.', 'danger')
        return redirect(url_for('auth.login'))
    
    today = date.today()
    
    # Métriques de performance
    metrics = {
        'weekly_load': player.get_weekly_load(),
        'acwr': player.get_acwr(),
        'fitness': player.get_fitness(),
        'fatigue': player.get_fatigue(),
        'tsb': player.get_tsb(),
        'form_status': player.get_form_status()
    }
    
    # Prochaines séances
    upcoming_sessions = TrainingSession.query.filter(
        TrainingSession.date >= today,
        TrainingSession.players.any(id=player.id)
    ).order_by(TrainingSession.date, TrainingSession.start_time).limit(5).all()
    
    # Dernières performances
    recent_results = TrainingResult.query.filter_by(player_id=player.id).order_by(
        TrainingResult.recorded_at.desc()
    ).limit(5).all()
    
    # Recommandations actives
    recommendations = Recommendation.query.filter_by(
        player_id=player.id,
        is_actioned=False
    ).order_by(Recommendation.priority.desc()).limit(3).all()
    
    # Dernier wellness
    last_wellness = WellnessRecord.query.filter_by(player_id=player.id).order_by(
        WellnessRecord.date.desc()
    ).first()
    
    # Vérifier si wellness rempli aujourd'hui
    wellness_today = WellnessRecord.query.filter_by(
        player_id=player.id,
        date=today
    ).first()
    
    return render_template('player/dashboard.html',
                          player=player,
                          metrics=metrics,
                          upcoming_sessions=upcoming_sessions,
                          recent_results=recent_results,
                          recommendations=recommendations,
                          last_wellness=last_wellness,
                          wellness_today=wellness_today is not None)


@player_portal_bp.route('/schedule')
@login_required
def schedule():
    """Planning du joueur"""
    player = get_current_player()
    if not player:
        return redirect(url_for('auth.login'))
    
    today = date.today()
    
    # Séances à venir
    upcoming = TrainingSession.query.filter(
        TrainingSession.date >= today,
        TrainingSession.players.any(id=player.id)
    ).order_by(TrainingSession.date).all()
    
    # Séances passées (30 derniers jours)
    past = TrainingSession.query.filter(
        TrainingSession.date < today,
        TrainingSession.date >= today - timedelta(days=30),
        TrainingSession.players.any(id=player.id)
    ).order_by(TrainingSession.date.desc()).all()
    
    return render_template('player/schedule.html',
                          player=player,
                          upcoming_sessions=upcoming,
                          past_sessions=past)


@player_portal_bp.route('/performances')
@login_required
def performances():
    """Historique des performances"""
    player = get_current_player()
    if not player:
        return redirect(url_for('auth.login'))
    
    # Tous les résultats
    results = TrainingResult.query.filter_by(player_id=player.id).order_by(
        TrainingResult.recorded_at.desc()
    ).limit(50).all()
    
    # Données GPS
    gps_history = GPSData.query.filter_by(player_id=player.id).order_by(
        GPSData.recorded_at.desc()
    ).limit(30).all()
    
    # Calculer les moyennes
    if results:
        avg_load = sum(r.training_load or 0 for r in results) / len(results)
        avg_rpe = sum(r.rpe or 0 for r in results if r.rpe) / len([r for r in results if r.rpe])
    else:
        avg_load = 0
        avg_rpe = 0
    
    if gps_history:
        avg_distance = sum(g.total_distance or 0 for g in gps_history) / len(gps_history)
        avg_hsr = sum(g.hsr_distance or 0 for g in gps_history) / len(gps_history)
    else:
        avg_distance = 0
        avg_hsr = 0
    
    averages = {
        'load': round(avg_load, 1),
        'rpe': round(avg_rpe, 1),
        'distance': round(avg_distance, 0),
        'hsr': round(avg_hsr, 0)
    }
    
    # Données pour graphiques
    chart_data = {
        'dates': [],
        'loads': [],
        'distances': []
    }
    
    for r in reversed(results[-20:]):
        if r.session:
            chart_data['dates'].append(r.session.date.strftime('%d/%m'))
            chart_data['loads'].append(r.training_load or 0)
    
    return render_template('player/performances.html',
                          player=player,
                          results=results,
                          gps_history=gps_history,
                          averages=averages,
                          chart_data=chart_data)


@player_portal_bp.route('/wellness', methods=['GET', 'POST'])
@login_required
def wellness():
    """Questionnaire de bien-être"""
    player = get_current_player()
    if not player:
        return redirect(url_for('auth.login'))
    
    today = date.today()
    form = WellnessForm()
    
    # Vérifier si déjà rempli aujourd'hui
    existing = WellnessRecord.query.filter_by(
        player_id=player.id,
        date=today
    ).first()
    
    if existing:
        form = WellnessForm(obj=existing)
    
    if form.validate_on_submit():
        if existing:
            record = existing
        else:
            record = WellnessRecord(player_id=player.id, date=today)
            db.session.add(record)
        
        record.fatigue = form.fatigue.data
        record.sleep_quality = form.sleep_quality.data
        record.sleep_hours = form.sleep_hours.data
        record.muscle_soreness = form.muscle_soreness.data
        record.stress = form.stress.data
        record.mood = form.mood.data
        record.hr_rest = form.hr_rest.data
        record.weight = form.weight.data
        record.notes = form.notes.data
        
        db.session.commit()
        
        flash('Questionnaire de bien-être enregistré !', 'success')
        return redirect(url_for('player_portal.dashboard'))
    
    # Historique wellness
    history = WellnessRecord.query.filter_by(player_id=player.id).order_by(
        WellnessRecord.date.desc()
    ).limit(14).all()
    
    return render_template('player/wellness.html',
                          player=player,
                          form=form,
                          existing=existing,
                          history=history)


@player_portal_bp.route('/recommendations')
@login_required
def recommendations():
    """Recommandations pour le joueur"""
    player = get_current_player()
    if not player:
        return redirect(url_for('auth.login'))
    
    recs = Recommendation.query.filter_by(player_id=player.id).order_by(
        Recommendation.created_at.desc()
    ).limit(20).all()
    
    return render_template('player/recommendations.html',
                          player=player,
                          recommendations=recs)


@player_portal_bp.route('/recommendations/<int:id>/read', methods=['POST'])
@login_required
def mark_recommendation_read(id):
    """Marquer une recommandation comme lue"""
    rec = Recommendation.query.get_or_404(id)
    rec.is_read = True
    db.session.commit()
    
    return redirect(url_for('player_portal.recommendations'))


@player_portal_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Mettre à jour le profil du joueur"""
    player = get_current_player()
    if not player:
        flash('Profil joueur non trouvé.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Récupérer les données du formulaire
    player.first_name = request.form.get('first_name', player.first_name)
    player.last_name = request.form.get('last_name', player.last_name)
    player.phone = request.form.get('phone') or None
    player.email = request.form.get('email') or None
    
    # Mettre à jour les paramètres sportifs
    try:
        weight = request.form.get('weight')
        if weight:
            player.weight = float(weight)
        
        height = request.form.get('height')
        if height:
            player.height = float(height)
        
        hr_max = request.form.get('hr_max')
        if hr_max:
            player.hr_max = int(hr_max)
    except (ValueError, TypeError):
        pass
    
    player.dominant_foot = request.form.get('dominant_foot') or None
    player.notes = request.form.get('notes') or None
    
    try:
        db.session.commit()
        flash('Profil mis à jour avec succès !', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la mise à jour : {str(e)}', 'danger')
    
    return redirect(url_for('player_portal.profile'))
