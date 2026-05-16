"""
RajaTracker - Routes Joueurs
=================================
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import db, Player, Team, TrainingResult, GPSData
from app.forms import PlayerForm
import os
from datetime import datetime

players_bp = Blueprint('players', __name__)

# Dossier uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads', 'players')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def save_player_photo(file):
    """Sauvegarde la photo du joueur et retourne le chemin"""
    try:
        if not file or file.filename == '':
            return None
        
        # Vérifier que c'est une image
        if not ('image' in file.content_type):
            return None
        
        # Générer un nom unique pour la photo
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        clean_filename = secure_filename(file.filename)
        
        if not clean_filename:
            return None
            
        full_filename = f"{timestamp}_{clean_filename}"
        filepath = os.path.join(UPLOAD_FOLDER, full_filename)
        
        # Créer le dossier s'il n'existe pas
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Sauvegarder le fichier
        file.save(filepath)
        print(f"✅ Photo sauvegardée: {filepath}")
        
        # Retourner le chemin relatif pour la base de données
        return f'players/{full_filename}'
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde de la photo: {str(e)}")
        return None


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
        
        # Gérer le upload de photo
        if form.photo.data:
            photo_path = save_player_photo(form.photo.data)
            if photo_path:
                player.photo_url = photo_path
                flash(f'Photo de profil ajoutée ✅', 'success')
        
        db.session.add(player)
        db.session.commit()
        
        flash(f'Joueur {player.full_name} ajouté avec succès !', 'success')
        return redirect(url_for('players.list_players'))
    else:
        # Afficher les erreurs de validation
        if form.errors:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'Erreur ({field}): {error}', 'danger')
    
    return render_template('coach/players/form.html', form=form, title='Ajouter un joueur')


@players_bp.route('/<int:id>')
@login_required
def view_player(id):
    """Voir un joueur avec analyses GPS + prediction IA"""
    from app.ml.predict import predict_from_player_db
    from app.ml.explain import explain_prediction
    from sqlalchemy import func

    player = Player.query.get_or_404(id)

    # Metriques de charge (existant)
    metrics = {
        'weekly_load': player.get_weekly_load(),
        'acwr': player.get_acwr(),
        'fitness': player.get_fitness(),
        'fatigue': player.get_fatigue(),
        'tsb': player.get_tsb(),
        'form_status': player.get_form_status()
    }

    # Dernieres performances (existant)
    recent_results = player.results.order_by(
        TrainingResult.recorded_at.desc()
    ).limit(10).all()

    # Toutes les donnees GPS (ordre chronologique pour les graphiques)
    all_gps = player.gps_data.order_by(GPSData.recorded_at.asc()).all()
    recent_gps = list(reversed(all_gps[-5:])) if all_gps else []

    # Statistiques GPS globales
    gps_stats = None
    if all_gps:
        distances = [g.total_distance for g in all_gps if g.total_distance]
        loads = [g.player_load for g in all_gps if g.player_load]
        speeds = [g.max_speed for g in all_gps if g.max_speed]
        sprints = [g.sprint_distance for g in all_gps if g.sprint_distance]

        gps_stats = {
            'nb_sessions': len(all_gps),
            'avg_distance': round(sum(distances) / len(distances)) if distances else 0,
            'max_distance': round(max(distances)) if distances else 0,
            'avg_load': round(sum(loads) / len(loads), 1) if loads else 0,
            'max_load': round(max(loads), 1) if loads else 0,
            'avg_speed': round(sum(speeds) / len(speeds), 2) if speeds else 0,
            'max_speed': round(max(speeds), 2) if speeds else 0,
            'total_sprints': round(sum(sprints)) if sprints else 0,
        }

    # Donnees pour les graphiques Chart.js (serialisable JSON)
    chart_data = {
        'labels': [],
        'distances': [],
        'loads': [],
        'speeds': [],
        'sprints': [],
    }
    for g in all_gps:
        if g.recorded_at:
            chart_data['labels'].append(g.recorded_at.strftime('%d/%m/%Y'))
        else:
            chart_data['labels'].append('-')
        chart_data['distances'].append(round(g.total_distance) if g.total_distance else 0)
        chart_data['loads'].append(round(g.player_load, 1) if g.player_load else 0)
        chart_data['speeds'].append(round(g.max_speed, 2) if g.max_speed else 0)
        chart_data['sprints'].append(round(g.sprint_distance) if g.sprint_distance else 0)

    # Prediction IA + explication
    ai_prediction = None
    ai_explanation = None
    try:
        ai_prediction = predict_from_player_db(player)
        ai_explanation = explain_prediction(
            {
                'age': player.age or 25,
                'position': player.position or 'Milieu',
                'acwr': metrics['acwr'] or 1.0,
                'wellness_avg_7d': 7.5,
                'wellness_avg_28d': 7.5,
                'sleep_avg_7d': 7.5,
                'sleep_avg_28d': 7.5,
                'acute_load': metrics['weekly_load'] or 0,
                'chronic_load': player.get_chronic_load() or 0,
                'acute_player_load': metrics['weekly_load'] or 0,
                'days_since_last_injury': None,
                'had_injury_30d': 0,
            },
            ai_prediction
        )
    except Exception as e:
        # En cas d'erreur, on continue sans IA
        ai_prediction = None
        ai_explanation = None

    return render_template('coach/players/view.html',
                          player=player,
                          metrics=metrics,
                          recent_results=recent_results,
                          recent_gps=recent_gps,
                          gps_stats=gps_stats,
                          chart_data=chart_data,
                          ai_prediction=ai_prediction,
                          ai_explanation=ai_explanation)


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
        
        # Gérer le upload de photo
        if form.photo.data:
            photo_path = save_player_photo(form.photo.data)
            if photo_path:
                player.photo_url = photo_path
                flash(f'Photo de profil mise à jour ✅', 'success')
        
        db.session.commit()
        flash(f'Joueur {player.full_name} modifié avec succès !', 'success')
        return redirect(url_for('players.view_player', id=id))
    else:
        # Afficher les erreurs de validation
        if form.errors:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'Erreur ({field}): {error}', 'danger')
    
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
