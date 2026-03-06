"""
SportTracker Pro - Routes Équipes
=================================
"""

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required
from app.models import db, Team, Player
from app.forms import TeamForm

teams_bp = Blueprint('teams', __name__)


@teams_bp.route('/')
@login_required
def list_teams():
    """Liste des équipes"""
    teams = Team.query.order_by(Team.name).all()
    return render_template('coach/teams/list.html', teams=teams)


@teams_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_team():
    """Ajouter une équipe"""
    form = TeamForm()
    
    if form.validate_on_submit():
        team = Team(
            name=form.name.data,
            category=form.category.data,
            description=form.description.data,
            target_weekly_load=form.target_weekly_load.data or 400,
            max_weekly_load=form.max_weekly_load.data or 600
        )
        
        db.session.add(team)
        db.session.commit()
        
        flash(f'Équipe {team.name} créée avec succès !', 'success')
        return redirect(url_for('teams.list_teams'))
    
    return render_template('coach/teams/form.html', form=form, title='Nouvelle équipe')


@teams_bp.route('/<int:id>')
@login_required
def view_team(id):
    """Voir une équipe"""
    team = Team.query.get_or_404(id)
    players = team.players.order_by(Player.last_name).all()
    
    from datetime import date, timedelta
    week_start = date.today() - timedelta(days=date.today().weekday())
    team_load = team.get_team_load(week_start)
    
    return render_template('coach/teams/view.html',
                          team=team,
                          players=players,
                          team_load=team_load)


@teams_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_team(id):
    """Modifier une équipe"""
    team = Team.query.get_or_404(id)
    form = TeamForm(obj=team)
    
    if form.validate_on_submit():
        form.populate_obj(team)
        db.session.commit()
        flash(f'Équipe {team.name} modifiée !', 'success')
        return redirect(url_for('teams.view_team', id=id))
    
    return render_template('coach/teams/form.html', form=form, team=team, title='Modifier')


@teams_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_team(id):
    """Supprimer une équipe"""
    team = Team.query.get_or_404(id)
    name = team.name
    
    for player in team.players:
        player.team_id = None
    
    db.session.delete(team)
    db.session.commit()
    
    flash(f'Équipe {name} supprimée.', 'info')
    return redirect(url_for('teams.list_teams'))
