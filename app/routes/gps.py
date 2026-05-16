"""
RajaTracker - Routes GPS
=============================
Import et visualisation des données GPS
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import pandas as pd
from datetime import datetime
from app.models import db, GPSData, TrainingSession, Player
from app.forms import GPSUploadForm

gps_bp = Blueprint('gps', __name__)


@gps_bp.route('/')
@login_required
def index():
    """Page principale GPS"""
    recent_imports = GPSData.query.order_by(GPSData.created_at.desc()).limit(20).all()
    sessions = TrainingSession.query.filter(
        TrainingSession.is_completed == False
    ).order_by(TrainingSession.date.desc()).limit(10).all()
    
    return render_template('coach/gps/index.html',
                          recent_imports=recent_imports,
                          sessions=sessions)


@gps_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Upload de fichier GPS"""
    form = GPSUploadForm()
    form.session_id.choices = [(s.id, f"{s.date} - {s.title}") 
                               for s in TrainingSession.query.order_by(
                                   TrainingSession.date.desc()
                               ).limit(20).all()]
    
    if form.validate_on_submit():
        file = form.file.data
        filename = secure_filename(file.filename)
        
        # Sauvegarder temporairement
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)
        
        try:
            # Parser le fichier selon le fournisseur
            provider = form.provider.data
            session_id = form.session_id.data
            
            records = parse_gps_file(upload_path, provider, session_id)
            
            flash(f'{len(records)} enregistrements GPS importés !', 'success')
            
        except Exception as e:
            flash(f'Erreur lors de l\'import : {str(e)}', 'danger')
        
        finally:
            # Supprimer le fichier temporaire
            if os.path.exists(upload_path):
                os.remove(upload_path)
        
        return redirect(url_for('gps.index'))
    
    return render_template('coach/gps/upload.html', form=form)


@gps_bp.route('/session/<int:session_id>')
@login_required
def session_data(session_id):
    """Données GPS d'une séance"""
    session = TrainingSession.query.get_or_404(session_id)
    gps_records = GPSData.query.filter_by(session_id=session_id).all()
    
    # Statistiques agrégées
    stats = {
        'avg_distance': 0,
        'avg_load': 0,
        'avg_hsr': 0,
        'max_speed': 0
    }
    
    if gps_records:
        stats['avg_distance'] = sum(r.total_distance or 0 for r in gps_records) / len(gps_records)
        stats['avg_load'] = sum(r.player_load or 0 for r in gps_records) / len(gps_records)
        stats['avg_hsr'] = sum(r.hsr_distance or 0 for r in gps_records) / len(gps_records)
        stats['max_speed'] = max(r.max_speed or 0 for r in gps_records)
    
    return render_template('coach/gps/session.html',
                          session=session,
                          gps_records=gps_records,
                          stats=stats)


@gps_bp.route('/player/<int:player_id>')
@login_required
def player_data(player_id):
    """Historique GPS d'un joueur"""
    player = Player.query.get_or_404(player_id)
    gps_history = GPSData.query.filter_by(player_id=player_id).order_by(
        GPSData.recorded_at.desc()
    ).limit(30).all()
    
    return render_template('coach/gps/player.html',
                          player=player,
                          gps_history=gps_history)


@gps_bp.route('/compare')
@login_required
def compare():
    """Comparaison de joueurs"""
    player_ids = request.args.getlist('players', type=int)
    session_id = request.args.get('session_id', type=int)
    
    players = Player.query.filter(Player.id.in_(player_ids)).all() if player_ids else []
    
    comparison_data = []
    for player in players:
        gps = GPSData.query.filter_by(
            player_id=player.id,
            session_id=session_id
        ).first() if session_id else None
        
        comparison_data.append({
            'player': player,
            'gps': gps
        })
    
    return render_template('coach/gps/compare.html',
                          comparison_data=comparison_data,
                          all_players=Player.query.all())


# =============================================================================
# FONCTIONS DE PARSING GPS
# =============================================================================

def parse_gps_file(filepath, provider, session_id):
    """
    Parse un fichier GPS selon le fournisseur.
    Retourne le nombre d'enregistrements créés.
    """
    records = []
    
    # Lire le fichier
    if filepath.endswith('.csv'):
        df = pd.read_csv(filepath)
    elif filepath.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(filepath)
    else:
        raise ValueError("Format de fichier non supporté")
    
    # Mapper les colonnes selon le fournisseur
    column_mapping = get_column_mapping(provider)
    
    # Récupérer la séance
    session = TrainingSession.query.get(session_id)
    if not session:
        raise ValueError("Séance non trouvée")
    
    for _, row in df.iterrows():
        # Trouver le joueur
        player_name = str(row.get(column_mapping.get('player_name', 'Player'), ''))
        player = find_player_by_name(player_name)
        
        if not player:
            continue
        
        # Créer ou mettre à jour l'enregistrement GPS
        gps = GPSData.query.filter_by(
            player_id=player.id,
            session_id=session_id
        ).first()
        
        if not gps:
            gps = GPSData(
                player_id=player.id,
                session_id=session_id,
                provider=provider
            )
            db.session.add(gps)
        
        # Mapper les données
        gps.total_distance = safe_float(row.get(column_mapping.get('total_distance')))
        gps.hsr_distance = safe_float(row.get(column_mapping.get('hsr_distance')))
        gps.sprint_distance = safe_float(row.get(column_mapping.get('sprint_distance')))
        gps.max_speed = safe_float(row.get(column_mapping.get('max_speed')))
        gps.avg_speed = safe_float(row.get(column_mapping.get('avg_speed')))
        gps.player_load = safe_float(row.get(column_mapping.get('player_load')))
        gps.accelerations = safe_int(row.get(column_mapping.get('accelerations')))
        gps.decelerations = safe_int(row.get(column_mapping.get('decelerations')))
        gps.hr_avg = safe_int(row.get(column_mapping.get('hr_avg')))
        gps.hr_max = safe_int(row.get(column_mapping.get('hr_max')))
        
        records.append(gps)
    
    db.session.commit()
    return records


def get_column_mapping(provider):
    """Retourne le mapping des colonnes selon le fournisseur GPS"""
    mappings = {
        'Catapult': {
            'player_name': 'Player Name',
            'total_distance': 'Total Distance',
            'hsr_distance': 'HSR Distance',
            'sprint_distance': 'Sprint Distance',
            'max_speed': 'Max Velocity',
            'avg_speed': 'Avg Velocity',
            'player_load': 'Player Load',
            'accelerations': 'Acceleration Count',
            'decelerations': 'Deceleration Count',
            'hr_avg': 'Avg HR',
            'hr_max': 'Max HR'
        },
        'STATSports': {
            'player_name': 'Player',
            'total_distance': 'Distance (m)',
            'hsr_distance': 'HSR (m)',
            'sprint_distance': 'Sprint Distance (m)',
            'max_speed': 'Max Speed (km/h)',
            'player_load': 'Dynamic Stress Load',
            'hr_avg': 'Avg Heart Rate',
            'hr_max': 'Max Heart Rate'
        },
        'Playertek': {
            'player_name': 'Name',
            'total_distance': 'Total Distance',
            'hsr_distance': 'High Speed Running',
            'sprint_distance': 'Sprint',
            'max_speed': 'Top Speed',
            'player_load': 'Load'
        },
        'GPExe': {
            'player_name': 'Athlete',
            'total_distance': 'Distance',
            'hsr_distance': 'Distance Z5',
            'sprint_distance': 'Distance Z6',
            'max_speed': 'Vmax',
            'player_load': 'Equivalent Distance'
        }
    }
    
    return mappings.get(provider, mappings['Catapult'])


def find_player_by_name(name):
    """Trouve un joueur par son nom"""
    if not name:
        return None
    
    parts = name.strip().split()
    if len(parts) >= 2:
        first_name = parts[0]
        last_name = ' '.join(parts[1:])
        
        player = Player.query.filter(
            db.func.lower(Player.first_name) == first_name.lower(),
            db.func.lower(Player.last_name) == last_name.lower()
        ).first()
        
        if player:
            return player
    
    # Recherche partielle
    return Player.query.filter(
        db.or_(
            Player.first_name.ilike(f'%{name}%'),
            Player.last_name.ilike(f'%{name}%')
        )
    ).first()


def safe_float(value):
    """Convertit en float de manière sécurisée"""
    try:
        return float(value) if pd.notna(value) else None
    except:
        return None


def safe_int(value):
    """Convertit en int de manière sécurisée"""
    try:
        return int(float(value)) if pd.notna(value) else None
    except:
        return None
