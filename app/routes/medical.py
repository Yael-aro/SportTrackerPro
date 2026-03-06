"""
SportTracker Pro - Routes Staff Médical
=======================================
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import date, timedelta
from app.models import db, Player, Injury, WellnessRecord, Recommendation
from app.forms import InjuryForm

medical_bp = Blueprint('medical', __name__)


@medical_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard médical"""
    # Joueurs blessés
    injured_players = Player.query.filter_by(status='Blessé').all()
    recovering_players = Player.query.filter(
        Player.status.in_(['En récupération', 'En rééducation'])
    ).all()
    
    # Blessures actives
    active_injuries = Injury.query.filter_by(is_active=True).order_by(
        Injury.date_injury.desc()
    ).all()
    
    # Joueurs à risque (basé sur ACWR et wellness)
    at_risk = []
    for player in Player.query.filter_by(status='Disponible').all():
        acwr = player.get_acwr()
        
        # Vérifier le wellness récent
        recent_wellness = WellnessRecord.query.filter_by(player_id=player.id).order_by(
            WellnessRecord.date.desc()
        ).first()
        
        wellness_score = recent_wellness.total_score if recent_wellness else 25
        
        if acwr > 1.3 or wellness_score < 15:
            at_risk.append({
                'player': player,
                'acwr': acwr,
                'wellness': wellness_score,
                'form': player.get_form_status()
            })
    
    at_risk.sort(key=lambda x: (x['acwr'], -x['wellness']), reverse=True)
    
    return render_template('medical/dashboard.html',
                          injured_players=injured_players,
                          recovering_players=recovering_players,
                          active_injuries=active_injuries,
                          at_risk=at_risk[:10])


@medical_bp.route('/injuries')
@login_required
def injuries():
    """Liste des blessures"""
    status = request.args.get('status', 'active')
    
    if status == 'active':
        injuries = Injury.query.filter_by(is_active=True).order_by(
            Injury.date_injury.desc()
        ).all()
    else:
        injuries = Injury.query.order_by(Injury.date_injury.desc()).all()
    
    return render_template('medical/injuries.html', injuries=injuries, status=status)


@medical_bp.route('/injuries/add', methods=['GET', 'POST'])
@login_required
def add_injury():
    """Ajouter une blessure"""
    form = InjuryForm()
    form.player_id.choices = [(p.id, p.full_name) for p in Player.query.order_by(Player.last_name).all()]
    
    if form.validate_on_submit():
        injury = Injury(
            player_id=form.player_id.data,
            injury_type=form.injury_type.data,
            body_part=form.body_part.data,
            severity=form.severity.data,
            date_injury=form.date_injury.data,
            expected_return=form.expected_return.data,
            mechanism=form.mechanism.data,
            context=form.context.data,
            treatment=form.treatment.data,
            notes=form.notes.data,
            recorded_by=current_user.id
        )
        
        db.session.add(injury)
        
        # Mettre à jour le statut du joueur
        player = Player.query.get(form.player_id.data)
        player.status = 'Blessé'
        
        db.session.commit()
        
        flash('Blessure enregistrée.', 'success')
        return redirect(url_for('medical.injuries'))
    
    return render_template('medical/injury_form.html', form=form, title='Nouvelle blessure')


@medical_bp.route('/injuries/<int:id>/return', methods=['POST'])
@login_required
def mark_return(id):
    """Marquer un joueur comme rétabli"""
    injury = Injury.query.get_or_404(id)
    
    injury.is_active = False
    injury.date_return = date.today()
    
    # Mettre à jour le statut du joueur
    player = injury.player
    player.status = 'Disponible'
    
    db.session.commit()
    
    flash(f'{player.full_name} est de retour !', 'success')
    return redirect(url_for('medical.dashboard'))


@medical_bp.route('/wellness')
@login_required
def wellness_overview():
    """Vue d'ensemble du bien-être"""
    today = date.today()
    
    # Wellness d'aujourd'hui
    today_records = WellnessRecord.query.filter_by(date=today).all()
    
    # Joueurs n'ayant pas rempli
    filled_ids = [r.player_id for r in today_records]
    missing = Player.query.filter(
        Player.status == 'Disponible',
        ~Player.id.in_(filled_ids)
    ).all()
    
    # Alertes (score < 15)
    alerts = [r for r in today_records if r.total_score < 15]
    
    return render_template('medical/wellness.html',
                          today_records=today_records,
                          missing=missing,
                          alerts=alerts)


@medical_bp.route('/player/<int:id>')
@login_required
def player_medical(id):
    """Fiche médicale d'un joueur"""
    player = Player.query.get_or_404(id)
    
    # Historique blessures
    injuries = Injury.query.filter_by(player_id=id).order_by(
        Injury.date_injury.desc()
    ).all()
    
    # Historique wellness
    wellness = WellnessRecord.query.filter_by(player_id=id).order_by(
        WellnessRecord.date.desc()
    ).limit(30).all()
    
    # Métriques
    metrics = {
        'acwr': player.get_acwr(),
        'tsb': player.get_tsb(),
        'form': player.get_form_status()
    }
    
    return render_template('medical/player.html',
                          player=player,
                          injuries=injuries,
                          wellness=wellness,
                          metrics=metrics)
