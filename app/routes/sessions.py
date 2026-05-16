"""
RajaTracker - Routes Séances
=================================
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import date, timedelta
from app.models import db, TrainingSession, Team, Player, TrainingResult
from app.forms import SessionForm, ResultForm

sessions_bp = Blueprint('sessions', __name__)


@sessions_bp.route('/')
@login_required
def list_sessions():
    """Liste des séances"""
    sessions = TrainingSession.query.order_by(TrainingSession.date.desc()).limit(50).all()
    return render_template('coach/sessions/list.html', sessions=sessions)


@sessions_bp.route('/calendar')
@login_required
def calendar():
    """Vue calendrier des séances"""
    teams = Team.query.all()
    return render_template('coach/sessions/calendar.html', teams=teams)


@sessions_bp.route('/api/events')
@login_required
def api_events():
    """API pour FullCalendar"""
    start = request.args.get('start')
    end = request.args.get('end')
    team_id = request.args.get('team_id', type=int)
    
    query = TrainingSession.query
    
    if start:
        query = query.filter(TrainingSession.date >= start[:10])
    if end:
        query = query.filter(TrainingSession.date <= end[:10])
    if team_id:
        query = query.filter(TrainingSession.team_id == team_id)
    
    sessions = query.all()
    
    events = []
    for s in sessions:
        events.append({
            'id': s.id,
            'title': s.title,
            'start': s.date.isoformat() + ('T' + s.start_time.strftime('%H:%M') if s.start_time else ''),
            'backgroundColor': s.type_color,
            'borderColor': s.type_color,
            'extendedProps': {
                'type': s.session_type,
                'duration': s.duration,
                'team': s.team.name if s.team else 'Tous',
                'completed': s.is_completed
            }
        })
    
    return jsonify(events)


@sessions_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_session():
    """Créer une séance"""
    form = SessionForm()
    form.team_id.choices = [(0, 'Tous les joueurs')] + [(t.id, t.name) for t in Team.query.all()]
    
    if form.validate_on_submit():
        session = TrainingSession(
            title=form.title.data,
            session_type=form.session_type.data,
            date=form.date.data,
            start_time=form.start_time.data,
            duration=form.duration.data,
            team_id=form.team_id.data if form.team_id.data != 0 else None,
            description=form.description.data,
            objectives=form.objectives.data,
            target_load=form.target_load.data,
            target_distance=form.target_distance.data,
            created_by=current_user.id
        )
        
        db.session.add(session)
        db.session.commit()
        
        # Ajouter les joueurs de l'équipe
        if session.team_id:
            for player in Team.query.get(session.team_id).players:
                session.players.append(player)
            db.session.commit()
        
        flash(f'Séance "{session.title}" créée !', 'success')
        return redirect(url_for('sessions.calendar'))
    
    return render_template('coach/sessions/form.html', form=form, title='Nouvelle séance')


@sessions_bp.route('/<int:id>')
@login_required
def view_session(id):
    """Voir une séance"""
    session = TrainingSession.query.get_or_404(id)
    
    # Résultats par joueur
    results = {}
    for result in session.results:
        results[result.player_id] = result
    
    return render_template('coach/sessions/view.html',
                          session=session,
                          results=results)


@sessions_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_session(id):
    """Modifier une séance"""
    session = TrainingSession.query.get_or_404(id)
    form = SessionForm(obj=session)
    form.team_id.choices = [(0, 'Tous')] + [(t.id, t.name) for t in Team.query.all()]
    
    if form.validate_on_submit():
        form.populate_obj(session)
        if form.team_id.data == 0:
            session.team_id = None
        db.session.commit()
        
        flash('Séance modifiée !', 'success')
        return redirect(url_for('sessions.view_session', id=id))
    
    return render_template('coach/sessions/form.html', form=form, session=session, title='Modifier')


@sessions_bp.route('/<int:id>/complete', methods=['POST'])
@login_required
def complete_session(id):
    """Marquer une séance comme terminée"""
    session = TrainingSession.query.get_or_404(id)
    session.is_completed = True
    db.session.commit()
    
    flash('Séance marquée comme terminée.', 'success')
    return redirect(url_for('sessions.view_session', id=id))


@sessions_bp.route('/<int:id>/results', methods=['GET', 'POST'])
@login_required
def enter_results(id):
    """Saisir les résultats d'une séance"""
    session = TrainingSession.query.get_or_404(id)
    
    if request.method == 'POST':
        # Traiter les résultats en masse
        for player in session.players:
            rpe = request.form.get(f'rpe_{player.id}', type=int)
            technical = request.form.get(f'technical_{player.id}', type=float)
            
            if rpe:
                result = TrainingResult.query.filter_by(
                    player_id=player.id,
                    session_id=session.id
                ).first()
                
                if not result:
                    result = TrainingResult(
                        player_id=player.id,
                        session_id=session.id
                    )
                    db.session.add(result)
                
                result.rpe = rpe
                result.technical_rating = technical
                result.calculate_load(session.duration)
                result.recorded_by = current_user.id
        
        db.session.commit()
        flash('Résultats enregistrés !', 'success')
        return redirect(url_for('sessions.view_session', id=id))
    
    # Récupérer les résultats existants
    existing = {r.player_id: r for r in session.results}
    
    return render_template('coach/sessions/results.html',
                          session=session,
                          existing=existing)


@sessions_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_session(id):
    """Supprimer une séance"""
    session = TrainingSession.query.get_or_404(id)
    
    db.session.delete(session)
    db.session.commit()
    
    flash('Séance supprimée.', 'info')
    return redirect(url_for('sessions.calendar'))
