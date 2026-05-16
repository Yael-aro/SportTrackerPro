"""
RajaTracker - Modèles de Données
=====================================
Modèles SQLAlchemy pour la gestion des joueurs, équipes, séances,
données GPS et analyses ML.

Auteur: Zakaria Mihrab
Version: 2.0 (PFE)
"""

from datetime import date, datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


# =============================================================================
# TABLE D'ASSOCIATION (Many-to-Many)
# =============================================================================

player_session = db.Table('player_session',
    db.Column('player_id', db.Integer, db.ForeignKey('player.id'), primary_key=True),
    db.Column('session_id', db.Integer, db.ForeignKey('training_session.id'), primary_key=True),
    db.Column('attended', db.Boolean, default=True)
)


# =============================================================================
# MODÈLE USER (Utilisateurs Multi-Rôles)
# =============================================================================

class User(db.Model):
    """
    Utilisateur de la plateforme avec gestion des rôles.
    Rôles: admin, coach, preparateur, medical, analyst, player, dirigeant
    Implémente UserMixin pour Flask-Login
    """
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)  # Nullable pour joueurs
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(30), nullable=False, default='coach')
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    
    # Lien vers joueur si l'utilisateur est un joueur
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
# Reset password (Etape 2)
    reset_token = db.Column(db.String(100), nullable=True, index=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)    

    # 2FA TOTP (Etape 2)
    totp_secret = db.Column(db.String(32), nullable=True)
    totp_enabled = db.Column(db.Boolean, default=False)
    # Relations
    player = db.relationship('Player', backref='user_account', foreign_keys=[player_id])
    
    # =========================================================================
    # Méthodes Flask-Login (OBLIGATOIRES)
    # =========================================================================
    
    def get_id(self):
        """Retourne l'ID de l'utilisateur comme string (requis par Flask-Login)"""
        return str(self.id)
    
    @property
    def is_authenticated(self):
        """Retourne True si l'utilisateur est authentifié"""
        return True
    
    @property
    def is_anonymous(self):
        """Retourne False car ce n'est pas un utilisateur anonyme"""
        return False
    
    # Rôles disponibles
    ROLES = {
        'admin': 'Administrateur',
        'coach': 'Entraîneur Principal',
        'assistant': 'Entraîneur Adjoint',
        'preparateur': 'Préparateur Physique',
        'medical': 'Staff Médical',
        'analyst': 'Analyste',
        'player': 'Joueur',
        'dirigeant': 'Dirigeant'
    }
    
    def set_password(self, password):
        """Hasher le mot de passe"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password):
        """Vérifier le mot de passe"""
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def role_display(self):
        return self.ROLES.get(self.role, self.role)
    
    def has_permission(self, permission):
        """Vérifier si l'utilisateur a une permission spécifique"""
        permissions = {
            'admin': ['all'],
            'coach': ['players', 'teams', 'sessions', 'gps', 'results', 'dashboard', 'reports'],
            'assistant': ['players_read', 'sessions', 'results', 'dashboard'],
            'preparateur': ['players', 'sessions', 'gps', 'results', 'dashboard', 'ml'],
            'medical': ['players_medical', 'injuries', 'wellness', 'dashboard'],
            'analyst': ['gps', 'results', 'dashboard', 'reports'],
            'player': ['own_profile', 'own_stats', 'own_schedule'],
            'dirigeant': ['reports', 'dashboard_summary']
        }
        user_permissions = permissions.get(self.role, [])
        return 'all' in user_permissions or permission in user_permissions
    
    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


# =============================================================================
# MODÈLE TEAM (Équipes)
# =============================================================================

class Team(db.Model):
    """
    Équipe ou groupe d'entraînement.
    Une équipe contient plusieurs joueurs.
    """
    __tablename__ = 'team'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    category = db.Column(db.String(30))  # Seniors, U19, U17, etc.
    
    # Objectifs de charge
    target_weekly_load = db.Column(db.Float, default=400)
    max_weekly_load = db.Column(db.Float, default=600)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    players = db.relationship('Player', backref='team', lazy='dynamic')
    sessions = db.relationship('TrainingSession', backref='team', lazy='dynamic')
    
    @property
    def player_count(self):
        """Nombre total de joueurs"""
        return self.players.count()
    
    @property
    def available_players(self):
        """Nombre de joueurs disponibles"""
        return self.players.filter_by(status='Disponible').count()
    
    @property
    def injured_players(self):
        """Nombre de joueurs blessés"""
        return self.players.filter_by(status='Blessé').count()
    
    def get_team_load(self, week_start=None):
        """Calcule la charge moyenne de l'équipe pour une semaine"""
        if week_start is None:
            week_start = date.today() - timedelta(days=date.today().weekday())
        
        total_load = 0
        count = 0
        for player in self.players:
            load = player.get_weekly_load(week_start)
            if load > 0:
                total_load += load
                count += 1
        
        return total_load / count if count > 0 else 0
    
    def __repr__(self):
        return f"<Team {self.name}>"


# =============================================================================
# MODÈLE PLAYER (Joueurs)
# =============================================================================

class Player(db.Model):
    """
    Joueur avec ses informations personnelles, sportives et médicales.
    """
    __tablename__ = 'player'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    
    # Informations sportives
    position = db.Column(db.String(30), nullable=False)
    jersey_number = db.Column(db.Integer)
    dominant_foot = db.Column(db.String(10))  # Droit, Gauche, Ambidextre
    height = db.Column(db.Float)  # en cm
    weight = db.Column(db.Float)  # en kg
    
    # Statut
    status = db.Column(db.String(30), default='Disponible')
    # Disponible, Blessé, Fatigué, En récupération, En rééducation, Suspendu
    
    # Équipe
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'))
    
    # Données personnelles
    photo_url = db.Column(db.String(255))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    
    # Seuils personnalisés (pour le GPS)
    hr_max = db.Column(db.Integer)  # FC max mesurée
    vma = db.Column(db.Float)  # VMA en km/h
    
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    sessions = db.relationship('TrainingSession', secondary=player_session,
                               backref=db.backref('players', lazy='dynamic'))
    results = db.relationship('TrainingResult', backref='player', lazy='dynamic',
                              cascade='all, delete-orphan')
    gps_data = db.relationship('GPSData', backref='player', lazy='dynamic',
                               cascade='all, delete-orphan')
    injuries = db.relationship('Injury', backref='player', lazy='dynamic',
                               cascade='all, delete-orphan')
    wellness_records = db.relationship('WellnessRecord', backref='player', lazy='dynamic',
                                       cascade='all, delete-orphan')
    
    # Positions disponibles
    POSITIONS = ['Gardien', 'Défenseur', 'Milieu', 'Attaquant']
    STATUSES = ['Disponible', 'Blessé', 'Fatigué', 'En récupération', 'En rééducation', 'Suspendu']
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self):
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
    
    @property
    def bmi(self):
        """Calcule l'IMC"""
        if self.height and self.weight:
            height_m = self.height / 100
            return round(self.weight / (height_m ** 2), 1)
        return None
    
    def get_weekly_load(self, week_start=None):
        """Calcule la charge d'entraînement sur une semaine (Acute Load)"""
        if week_start is None:
            week_start = date.today() - timedelta(days=date.today().weekday())
        
        week_end = week_start + timedelta(days=7)
        
        results = TrainingResult.query.join(TrainingSession).filter(
            TrainingResult.player_id == self.id,
            TrainingSession.date >= week_start,
            TrainingSession.date < week_end
        ).all()
        
        return sum(r.training_load or 0 for r in results)
    
    def get_chronic_load(self, end_date=None, weeks=4):
        """Calcule la charge chronique (moyenne sur 4 semaines)"""
        if end_date is None:
            end_date = date.today()
        
        total_load = 0
        for i in range(weeks):
            week_start = end_date - timedelta(days=7 * (i + 1))
            total_load += self.get_weekly_load(week_start)
        
        return total_load / weeks
    
    def get_acwr(self):
        """Calcule le ratio Acute:Chronic Workload Ratio"""
        acute = self.get_weekly_load()
        chronic = self.get_chronic_load()
        
        if chronic > 0:
            return round(acute / chronic, 2)
        return 0
    
    def get_fitness(self, days=42):
        """Calcule le niveau de fitness (CTL - Chronic Training Load)"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        results = TrainingResult.query.join(TrainingSession).filter(
            TrainingResult.player_id == self.id,
            TrainingSession.date >= start_date,
            TrainingSession.date <= end_date
        ).all()
        
        if not results:
            return 0
        
        # Moyenne pondérée exponentielle
        total = sum(r.training_load or 0 for r in results)
        return round(total / days, 1)
    
    def get_fatigue(self, days=7):
        """Calcule le niveau de fatigue (ATL - Acute Training Load)"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        results = TrainingResult.query.join(TrainingSession).filter(
            TrainingResult.player_id == self.id,
            TrainingSession.date >= start_date,
            TrainingSession.date <= end_date
        ).all()
        
        if not results:
            return 0
        
        total = sum(r.training_load or 0 for r in results)
        return round(total / days, 1)
    
    def get_tsb(self):
        """Calcule le Training Stress Balance (Form)"""
        return round(self.get_fitness() - self.get_fatigue(), 1)
    
    def get_form_status(self):
        """Retourne le statut de forme basé sur TSB et ACWR"""
        tsb = self.get_tsb()
        acwr = self.get_acwr()
        
        if acwr > 1.5 or tsb < -20:
            return {'status': 'Danger', 'color': 'danger', 'icon': 'exclamation-triangle-fill'}
        elif acwr > 1.3 or tsb < -10:
            return {'status': 'Attention', 'color': 'warning', 'icon': 'exclamation-circle-fill'}
        elif tsb > 10:
            return {'status': 'Excellent', 'color': 'success', 'icon': 'check-circle-fill'}
        else:
            return {'status': 'Bon', 'color': 'info', 'icon': 'emoji-smile-fill'}
    
    def __repr__(self):
        return f"<Player {self.full_name}>"


# =============================================================================
# MODÈLE TRAINING SESSION (Séances d'entraînement)
# =============================================================================

class TrainingSession(db.Model):
    """
    Séance d'entraînement planifiée.
    """
    __tablename__ = 'training_session'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    session_type = db.Column(db.String(50), nullable=False)
    
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time)
    duration = db.Column(db.Integer, nullable=False)  # en minutes
    
    description = db.Column(db.Text)
    objectives = db.Column(db.Text)  # Objectifs de la séance
    
    # Charge cible
    target_load = db.Column(db.Float)
    target_distance = db.Column(db.Float)  # en km
    
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    is_completed = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    results = db.relationship('TrainingResult', backref='session', lazy='dynamic',
                              cascade='all, delete-orphan')
    gps_data = db.relationship('GPSData', backref='session', lazy='dynamic',
                               cascade='all, delete-orphan')
    
    # Types de séances
    SESSION_TYPES = [
        'Cardio', 'Musculation', 'Technique', 'Tactique', 
        'Récupération', 'Match amical', 'Évaluation', 'Mixte'
    ]
    
    @property
    def type_color(self):
        """Retourne la couleur associée au type de séance"""
        colors = {
            'Cardio': '#e74c3c',
            'Musculation': '#9b59b6',
            'Technique': '#3498db',
            'Tactique': '#2ecc71',
            'Récupération': '#1abc9c',
            'Match amical': '#f39c12',
            'Évaluation': '#e67e22',
            'Mixte': '#95a5a6'
        }
        return colors.get(self.session_type, '#7f8c8d')
    
    @property
    def player_count(self):
        """Nombre de joueurs assignés"""
        return len(self.players.all())
    
    @property
    def completion_rate(self):
        """Taux de complétion (résultats saisis / joueurs)"""
        total = self.player_count
        if total == 0:
            return 0
        completed = self.results.count()
        return round((completed / total) * 100)
    
    def get_average_load(self):
        """Charge moyenne de la séance"""
        results = self.results.all()
        if not results:
            return 0
        total = sum(r.training_load or 0 for r in results)
        return round(total / len(results), 1)
    
    def __repr__(self):
        return f"<TrainingSession {self.title} ({self.date})>"


# =============================================================================
# MODÈLE GPS DATA (Données GPS)
# =============================================================================

class GPSData(db.Model):
    """
    Données collectées par les gilets GPS.
    Stocke les métriques brutes importées des fichiers GPS.
    """
    __tablename__ = 'gps_data'
    
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('training_session.id'), nullable=False)
    
    # Métadonnées
    device_id = db.Column(db.String(50))  # ID du gilet
    provider = db.Column(db.String(30))  # Catapult, STATSports, etc.
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # === MÉTRIQUES DE DISTANCE ===
    total_distance = db.Column(db.Float)  # Distance totale (m)
    hsr_distance = db.Column(db.Float)    # Distance haute intensité > 19.8 km/h (m)
    sprint_distance = db.Column(db.Float)  # Distance sprint > 25.2 km/h (m)
    distance_zone_1 = db.Column(db.Float)  # 0-6 km/h
    distance_zone_2 = db.Column(db.Float)  # 6-12 km/h
    distance_zone_3 = db.Column(db.Float)  # 12-18 km/h
    distance_zone_4 = db.Column(db.Float)  # 18-21 km/h
    distance_zone_5 = db.Column(db.Float)  # 21-24 km/h
    distance_zone_6 = db.Column(db.Float)  # > 24 km/h
    
    # === MÉTRIQUES DE VITESSE ===
    max_speed = db.Column(db.Float)      # Vitesse maximale (km/h)
    avg_speed = db.Column(db.Float)      # Vitesse moyenne (km/h)
    max_speed_efforts = db.Column(db.Integer)  # Nombre de sprints max
    
    # === MÉTRIQUES D'ACCÉLÉRATION ===
    accelerations = db.Column(db.Integer)     # Nb accélérations > 3 m/s²
    decelerations = db.Column(db.Integer)     # Nb décélérations > -3 m/s²
    high_accelerations = db.Column(db.Integer)  # > 4 m/s²
    high_decelerations = db.Column(db.Integer)  # < -4 m/s²
    
    # === MÉTRIQUES DE CHARGE ===
    player_load = db.Column(db.Float)         # Player Load (UA)
    player_load_per_min = db.Column(db.Float)  # PL/min
    
    # === MÉTRIQUES CARDIAQUES ===
    hr_avg = db.Column(db.Integer)      # FC moyenne (bpm)
    hr_max = db.Column(db.Integer)      # FC max atteinte (bpm)
    hr_min = db.Column(db.Integer)      # FC min (bpm)
    time_hr_zone_1 = db.Column(db.Integer)  # Temps zone 1 (sec)
    time_hr_zone_2 = db.Column(db.Integer)  # Temps zone 2 (sec)
    time_hr_zone_3 = db.Column(db.Integer)  # Temps zone 3 (sec)
    time_hr_zone_4 = db.Column(db.Integer)  # Temps zone 4 (sec)
    time_hr_zone_5 = db.Column(db.Integer)  # Temps zone 5 > 90% (sec)
    hr_exertion = db.Column(db.Float)  # Indice d'effort cardiaque
    
    # === MÉTRIQUES MÉTABOLIQUES ===
    metabolic_power_avg = db.Column(db.Float)  # Puissance métabolique moyenne (W/kg)
    metabolic_power_max = db.Column(db.Float)  # Puissance métabolique max
    energy_expenditure = db.Column(db.Float)   # Dépense énergétique (kcal)
    
    # === DONNÉES DE POSITION ===
    heatmap_data = db.Column(db.JSON)  # Coordonnées XY pour heatmap
    avg_position_x = db.Column(db.Float)
    avg_position_y = db.Column(db.Float)
    
    # === DURÉES ===
    duration_active = db.Column(db.Integer)  # Temps actif (sec)
    duration_total = db.Column(db.Integer)   # Temps total (sec)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Fournisseurs supportés
    PROVIDERS = ['Catapult', 'STATSports', 'Playertek', 'GPExe', 'Polar', 'Kinexon', 'Autre']
    
    @property
    def hsr_percentage(self):
        """Pourcentage de distance à haute intensité"""
        if self.total_distance and self.total_distance > 0:
            return round((self.hsr_distance or 0) / self.total_distance * 100, 1)
        return 0
    
    @property
    def sprint_percentage(self):
        """Pourcentage de distance en sprint"""
        if self.total_distance and self.total_distance > 0:
            return round((self.sprint_distance or 0) / self.total_distance * 100, 1)
        return 0
    
    def __repr__(self):
        return f"<GPSData Player:{self.player_id} Session:{self.session_id}>"


# =============================================================================
# MODÈLE TRAINING RESULT (Résultats d'entraînement)
# =============================================================================

class TrainingResult(db.Model):
    """
    Résultats et performances d'un joueur pour une séance.
    Combine les données GPS avec les données subjectives (RPE).
    """
    __tablename__ = 'training_result'
    
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('training_session.id'), nullable=False)
    gps_data_id = db.Column(db.Integer, db.ForeignKey('gps_data.id'))
    
    # Données subjectives
    rpe = db.Column(db.Integer)  # Rate of Perceived Exertion (1-10)
    wellness_pre = db.Column(db.Integer)  # Score bien-être pré-séance
    
    # Charge calculée
    training_load = db.Column(db.Float)  # sRPE = durée × RPE
    
    # Notes techniques
    technical_rating = db.Column(db.Float)  # Note technique (1-10)
    tactical_rating = db.Column(db.Float)   # Note tactique (1-10)
    
    # Métriques calculées
    acwr = db.Column(db.Float)  # Ratio Acute:Chronic
    tsb = db.Column(db.Float)   # Training Stress Balance
    monotony = db.Column(db.Float)  # Monotonie de la charge
    strain = db.Column(db.Float)    # Contrainte
    
    # Prédictions ML
    injury_risk = db.Column(db.Float)  # Probabilité de blessure (0-1)
    recommended_load = db.Column(db.Float)  # Charge recommandée
    
    notes = db.Column(db.Text)
    
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    recorded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relation avec GPS
    gps = db.relationship('GPSData', backref='result')
    
    # Contrainte d'unicité
    __table_args__ = (
        db.UniqueConstraint('player_id', 'session_id', name='unique_player_session_result'),
    )
    
    def calculate_load(self, duration=None):
        """Calcule la charge sRPE"""
        if duration is None and self.session:
            duration = self.session.duration
        
        if self.rpe and duration:
            self.training_load = self.rpe * duration
            return self.training_load
        return 0
    
    @property
    def load_level(self):
        """Niveau de charge de la séance"""
        if not self.training_load:
            return {'text': 'Non défini', 'color': 'secondary'}
        
        if self.training_load < 200:
            return {'text': 'Légère', 'color': 'success'}
        elif self.training_load < 400:
            return {'text': 'Modérée', 'color': 'info'}
        elif self.training_load < 600:
            return {'text': 'Élevée', 'color': 'warning'}
        else:
            return {'text': 'Très élevée', 'color': 'danger'}
    
    def __repr__(self):
        return f"<TrainingResult Player:{self.player_id} Session:{self.session_id}>"


# =============================================================================
# MODÈLE INJURY (Blessures)
# =============================================================================

class Injury(db.Model):
    """
    Historique des blessures d'un joueur.
    """
    __tablename__ = 'injury'
    
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    
    injury_type = db.Column(db.String(100), nullable=False)  # Type de blessure
    body_part = db.Column(db.String(50), nullable=False)     # Partie du corps
    severity = db.Column(db.String(30))  # Légère, Modérée, Grave
    
    date_injury = db.Column(db.Date, nullable=False)
    date_return = db.Column(db.Date)
    expected_return = db.Column(db.Date)
    
    mechanism = db.Column(db.String(100))  # Mécanisme de blessure
    context = db.Column(db.String(50))     # Match, Entraînement, Autre
    
    treatment = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    is_active = db.Column(db.Boolean, default=True)
    
    recorded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Types de blessures courantes
    INJURY_TYPES = [
        'Entorse', 'Élongation', 'Claquage', 'Contusion', 'Fracture',
        'Tendinite', 'Pubalgie', 'Lombalgie', 'Commotion', 'Autre'
    ]
    
    BODY_PARTS = [
        'Cheville', 'Genou', 'Cuisse', 'Mollet', 'Hanche',
        'Dos', 'Épaule', 'Tête', 'Pied', 'Autre'
    ]
    
    @property
    def days_out(self):
        """Nombre de jours d'absence"""
        if self.date_return:
            return (self.date_return - self.date_injury).days
        elif self.is_active:
            return (date.today() - self.date_injury).days
        return 0
    
    def __repr__(self):
        return f"<Injury {self.injury_type} - Player:{self.player_id}>"


# =============================================================================
# MODÈLE WELLNESS RECORD (Bien-être)
# =============================================================================

class WellnessRecord(db.Model):
    """
    Questionnaire de bien-être quotidien.
    """
    __tablename__ = 'wellness_record'
    
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    
    date = db.Column(db.Date, nullable=False, default=date.today)
    
    # Scores (1-5 chacun, total sur 25)
    fatigue = db.Column(db.Integer)       # 1=Très fatigué, 5=Très frais
    sleep_quality = db.Column(db.Integer)  # 1=Très mauvais, 5=Excellent
    sleep_hours = db.Column(db.Float)      # Heures de sommeil
    muscle_soreness = db.Column(db.Integer)  # 1=Très douloureux, 5=Aucune douleur
    stress = db.Column(db.Integer)         # 1=Très stressé, 5=Très détendu
    mood = db.Column(db.Integer)           # 1=Très mauvais, 5=Excellent
    
    # Données complémentaires
    hr_rest = db.Column(db.Integer)  # FC au repos (bpm)
    weight = db.Column(db.Float)     # Poids du jour (kg)
    
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Contrainte d'unicité (un enregistrement par jour par joueur)
    __table_args__ = (
        db.UniqueConstraint('player_id', 'date', name='unique_player_date_wellness'),
    )
    
    @property
    def total_score(self):
        """Score total de bien-être (sur 25)"""
        scores = [self.fatigue, self.sleep_quality, self.muscle_soreness, 
                  self.stress, self.mood]
        valid_scores = [s for s in scores if s is not None]
        return sum(valid_scores) if valid_scores else 0
    
    @property
    def wellness_status(self):
        """Statut de bien-être"""
        total = self.total_score
        if total >= 20:
            return {'status': 'Excellent', 'color': 'success'}
        elif total >= 15:
            return {'status': 'Bon', 'color': 'info'}
        elif total >= 10:
            return {'status': 'Moyen', 'color': 'warning'}
        else:
            return {'status': 'Faible', 'color': 'danger'}
    
    def __repr__(self):
        return f"<WellnessRecord Player:{self.player_id} Date:{self.date}>"


# =============================================================================
# MODÈLE RECOMMENDATION (Recommandations ML)
# =============================================================================

class Recommendation(db.Model):
    """
    Recommandations générées par les modèles ML.
    """
    __tablename__ = 'recommendation'
    
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    
    date = db.Column(db.Date, default=date.today)
    
    # Type de recommandation
    rec_type = db.Column(db.String(50), nullable=False)
    # load_reduction, rest_day, medical_check, load_increase, etc.
    
    priority = db.Column(db.String(20))  # Critique, Haute, Moyenne, Basse
    
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Données de contexte
    trigger_metric = db.Column(db.String(50))  # ACWR, TSB, wellness, etc.
    trigger_value = db.Column(db.Float)
    threshold_value = db.Column(db.Float)
    
    # Statut
    is_read = db.Column(db.Boolean, default=False)
    is_actioned = db.Column(db.Boolean, default=False)
    actioned_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    actioned_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relation
    player = db.relationship('Player', backref='recommendations')
    
    REC_TYPES = {
        'load_reduction': 'Réduction de charge',
        'rest_day': 'Jour de repos',
        'medical_check': 'Consultation médicale',
        'load_increase': 'Augmentation progressive',
        'recovery_session': 'Séance de récupération',
        'wellness_alert': 'Alerte bien-être'
    }
    
    @property
    def type_display(self):
        return self.REC_TYPES.get(self.rec_type, self.rec_type)
    
    @property
    def priority_color(self):
        colors = {
            'Critique': 'danger',
            'Haute': 'warning',
            'Moyenne': 'info',
            'Basse': 'secondary'
        }
        return colors.get(self.priority, 'secondary')
    
    def __repr__(self):
        return f"<Recommendation {self.rec_type} - Player:{self.player_id}>"


# =============================================================================
# MODELE AUDIT LOG (Etape 2 - Securite / Conformite RGPD)
# =============================================================================

class AuditLog(db.Model):
    """
    Journal d'audit : trace toutes les actions sensibles de la plateforme.
    Permet la tracabilite en cas d'incident de securite ou de litige RGPD.
    """
    __tablename__ = 'audit_log'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Qui a fait l'action
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    user_email = db.Column(db.String(120), nullable=True)  # Garde l'email meme si user supprime
    user_role = db.Column(db.String(30), nullable=True)

    # Quelle action
    action = db.Column(db.String(50), nullable=False, index=True)
    # Ex: 'login_success', 'login_failed', 'logout', 'player_created',
    #     'player_deleted', 'team_updated', '2fa_enabled', 'password_reset', etc.

    # Sur quoi
    target_type = db.Column(db.String(50), nullable=True)  # 'player', 'team', 'session'...
    target_id = db.Column(db.Integer, nullable=True)
    target_name = db.Column(db.String(200), nullable=True)  # Nom lisible

    # Details (JSON-like)
    details = db.Column(db.Text, nullable=True)

    # Contexte technique
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 ou IPv6
    user_agent = db.Column(db.String(255), nullable=True)

    # Relation
    user = db.relationship('User', foreign_keys=[user_id])

    def __repr__(self):
        return f"<AuditLog {self.action} by {self.user_email} at {self.timestamp}>"


def log_action(action, target_type=None, target_id=None, target_name=None, details=None, user=None):
    """
    Helper pour enregistrer une action dans le journal d'audit.

    Utilisation :
        log_action('player_created', target_type='player', target_id=p.id, target_name=p.full_name)
    """
    from flask import request
    from flask_login import current_user

    actor = user or (current_user if current_user.is_authenticated else None)

    entry = AuditLog(
        user_id=actor.id if actor else None,
        user_email=actor.email if actor else 'anonymous',
        user_role=actor.role if actor else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        target_name=target_name,
        details=details,
        ip_address=request.remote_addr if request else None,
        user_agent=request.headers.get('User-Agent', '')[:255] if request else None
    )
    db.session.add(entry)
    db.session.commit()
    return entry
