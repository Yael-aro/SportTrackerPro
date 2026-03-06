"""
SportTracker Pro - Routes Joueurs
=================================
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import db, Player, Team
from app.forms import PlayerForm

players_bp = Blueprint('players', __name__)


@players_bp.route('/')
@login_required
def list_players():
    """Liste des joueurs"""
    team_id = request.args.get('team_id', type=int)
    status = request.args.get('status')
    position = request.args.get('position')
    
    query = Player.query
    
    if team_id:
        query = query.filter_by(team_id=team_id)
    if status:
        query = query.filter_by(status=status)
    if position:
        query = query.filter_by(position=position)
    
    players = query.order_by(Player.last_name, Player.first_name).all()
    teams = Team.query.all()
    
    return render_template('coach/players/list.html', 
                          players=players, 
                          teams=teams)


@players_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_player():
    """Ajouter un joueur"""
    form = PlayerForm()
    form.team_id.choices = [(0, 'Sans équipe')] + [(t.id, t.name) for t in Team.query.all()]
    
    if form.validate_on_submit():
        player = Player(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            date_of_birth=form.date_of_birth.data,
            position=form.position.data,
            jersey_number=form.jersey_number.data,
            dominant_foot=form.dominant_foot.data or None,
            height=form.height.data,
            weight=form.weight.data,
            status=form.status.data,
            team_id=form.team_id.data if form.team_id.data != 0 else None,
            email=form.email.data,
            phone=form.phone.data,
            hr_max=form.hr_max.data,
            vma=form.vma.data,
            notes=form.notes.data
        )
        
        db.session.add(player)
        db.session.commit()
        
        flash(f'Joueur {player.full_name} ajouté avec succès !', 'success')
        return redirect(url_for('players.list_players'))
    
    return render_template('coach/players/form.html', form=form, title='Ajouter un joueur')


@players_bp.route('/<int:id>')
@login_required
def view_player(id):
    """Voir un joueur"""
    player = Player.query.get_or_404(id)
    
    # Calculer les métriques
    metrics = {
        'weekly_load': player.get_weekly_load(),
        'acwr': player.get_acwr(),
        'fitness': player.get_fitness(),
        'fatigue': player.get_fatigue(),
        'tsb': player.get_tsb(),
        'form_status': player.get_form_status()
    }
    
    # Dernières performances
    recent_results = player.results.order_by(
        TrainingResult.recorded_at.desc()
    ).limit(10).all()
    
    # Dernières données GPS
    recent_gps = player.gps_data.order_by(
        GPSData.recorded_at.desc()
    ).limit(5).all()
    
    return render_template('coach/players/view.html',
                          player=player,
                          metrics=metrics,
                          recent_results=recent_results,
                          recent_gps=recent_gps)


@players_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_player(id):
    """Modifier un joueur"""
    player = Player.query.get_or_404(id)
    form = PlayerForm(obj=player)
    form.team_id.choices = [(0, 'Sans équipe')] + [(t.id, t.name) for t in Team.query.all()]
    
    if form.validate_on_submit():
        form.populate_obj(player)
        if form.team_id.data == 0:
            player.team_id = None
        
        db.session.commit()
        flash(f'Joueur {player.full_name} modifié avec succès !', 'success')
        return redirect(url_for('players.view_player', id=id))
    
    return render_template('coach/players/form.html', 
                          form=form, 
                          player=player,
                          title='Modifier le joueur')


@players_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_player(id):
    """Supprimer un joueur"""
    player = Player.query.get_or_404(id)
    name = player.full_name
    
    db.session.delete(player)
    db.session.commit()
    
    flash(f'Joueur {name} supprimé.', 'info')
    return redirect(url_for('players.list_players'))


# Import nécessaire pour view_player
from app.models import TrainingResult, GPSData
