"""
SportTracker Pro - Formulaires WTForms
======================================
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileSize
from wtforms import (
    StringField, TextAreaField, SelectField, DateField, 
    TimeField, IntegerField, FloatField, BooleanField, 
    SelectMultipleField, SubmitField, PasswordField, EmailField
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional, Email, EqualTo, ValidationError
from app.models import Player, User


# =============================================================================
# FORMULAIRES D'AUTHENTIFICATION
# =============================================================================

class LoginForm(FlaskForm):
    """Formulaire de connexion"""
    
    email = EmailField('Email', validators=[
        DataRequired(message='L\'email est obligatoire'),
        Email(message='Email invalide')
    ])
    
    password = PasswordField('Mot de passe', validators=[
        DataRequired(message='Le mot de passe est obligatoire')
    ])
    
    remember = BooleanField('Se souvenir de moi')
    submit = SubmitField('Se connecter')


class RegisterForm(FlaskForm):
    """Formulaire d'inscription staff"""
    
    first_name = StringField('Prénom', validators=[
        DataRequired(message='Le prénom est obligatoire'),
        Length(min=2, max=50)
    ])
    
    last_name = StringField('Nom', validators=[
        DataRequired(message='Le nom est obligatoire'),
        Length(min=2, max=50)
    ])
    
    email = EmailField('Email', validators=[
        DataRequired(message='L\'email est obligatoire'),
        Email(message='Email invalide')
    ])
    
    phone = StringField('Téléphone', validators=[Optional(), Length(max=20)])
    
    password = PasswordField('Mot de passe', validators=[
        DataRequired(message='Le mot de passe est obligatoire'),
        Length(min=6, message='Le mot de passe doit contenir au moins 6 caractères')
    ])
    
    confirm_password = PasswordField('Confirmer', validators=[
        DataRequired(message='Confirmez le mot de passe'),
        EqualTo('password', message='Les mots de passe ne correspondent pas')
    ])
    
    role = SelectField('Rôle', choices=[
        ('coach', 'Entraîneur'),
        ('assistant', 'Entraîneur Adjoint'),
        ('preparateur', 'Préparateur Physique'),
        ('medical', 'Staff Médical'),
        ('analyst', 'Analyste'),
        ('dirigeant', 'Dirigeant')
    ], default='coach')
    
    submit = SubmitField('Créer mon compte')
    
    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('Cet email est déjà utilisé.')


# =============================================================================
# FORMULAIRES JOUEURS
# =============================================================================

class PlayerForm(FlaskForm):
    """Formulaire joueur"""
    
    first_name = StringField('Prénom', validators=[
        DataRequired(message='Le prénom est obligatoire'),
        Length(min=2, max=50)
    ])
    
    last_name = StringField('Nom', validators=[
        DataRequired(message='Le nom est obligatoire'),
        Length(min=2, max=50)
    ])
    
    date_of_birth = DateField('Date de naissance', validators=[
        DataRequired(message='La date de naissance est obligatoire')
    ])
    
    position = SelectField('Poste', choices=[
        ('Gardien', 'Gardien'),
        ('Défenseur', 'Défenseur'),
        ('Milieu', 'Milieu'),
        ('Attaquant', 'Attaquant')
    ])
    
    jersey_number = IntegerField('Numéro de maillot', validators=[
        Optional(),
        NumberRange(min=1, max=99)
    ])
    
    dominant_foot = SelectField('Pied fort', choices=[
        ('', 'Non spécifié'),
        ('Droit', 'Droit'),
        ('Gauche', 'Gauche'),
        ('Ambidextre', 'Ambidextre')
    ], validators=[Optional()])
    
    height = FloatField('Taille (cm)', validators=[
        Optional(),
        NumberRange(min=100, max=250)
    ])
    
    weight = FloatField('Poids (kg)', validators=[
        Optional(),
        NumberRange(min=30, max=150)
    ])
    
    status = SelectField('Statut', choices=[
        ('Disponible', 'Disponible'),
        ('Blessé', 'Blessé'),
        ('Fatigué', 'Fatigué'),
        ('En récupération', 'En récupération'),
        ('En rééducation', 'En rééducation'),
        ('Suspendu', 'Suspendu')
    ])
    
    team_id = SelectField('Équipe', coerce=int, validators=[Optional()])
    
    email = EmailField('Email', validators=[Optional(), Email()])
    phone = StringField('Téléphone', validators=[Optional(), Length(max=20)])
    
    hr_max = IntegerField('FC Max', validators=[
        Optional(),
        NumberRange(min=100, max=250)
    ])
    
    vma = FloatField('VMA (km/h)', validators=[
        Optional(),
        NumberRange(min=8, max=25)
    ])
    
    photo = FileField('Photo de profil', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images uniquement (jpg, jpeg, png, gif)'),
        FileSize(max_size=5*1024*1024, message='La photo ne doit pas dépasser 5MB')
    ])
    
    notes = TextAreaField('Notes', validators=[Optional()])
    
    submit = SubmitField('Enregistrer')


# =============================================================================
# FORMULAIRES ÉQUIPES
# =============================================================================

class TeamForm(FlaskForm):
    """Formulaire équipe"""
    
    name = StringField('Nom de l\'équipe', validators=[
        DataRequired(message='Le nom est obligatoire'),
        Length(min=2, max=100)
    ])
    
    category = SelectField('Catégorie', choices=[
        ('Seniors', 'Seniors'),
        ('U23', 'U23'),
        ('U21', 'U21'),
        ('U19', 'U19'),
        ('U17', 'U17'),
        ('U15', 'U15'),
        ('Autre', 'Autre')
    ], validators=[Optional()])
    
    description = TextAreaField('Description', validators=[Optional()])
    
    target_weekly_load = FloatField('Charge hebdo cible', validators=[
        Optional(),
        NumberRange(min=0, max=2000)
    ], default=400)
    
    max_weekly_load = FloatField('Charge hebdo max', validators=[
        Optional(),
        NumberRange(min=0, max=3000)
    ], default=600)
    
    submit = SubmitField('Enregistrer')


# =============================================================================
# FORMULAIRES SÉANCES
# =============================================================================

class SessionForm(FlaskForm):
    """Formulaire séance d'entraînement"""
    
    title = StringField('Titre', validators=[
        DataRequired(message='Le titre est obligatoire'),
        Length(min=2, max=100)
    ])
    
    session_type = SelectField('Type de séance', choices=[
        ('Cardio', 'Cardio'),
        ('Musculation', 'Musculation'),
        ('Technique', 'Technique'),
        ('Tactique', 'Tactique'),
        ('Récupération', 'Récupération'),
        ('Match amical', 'Match amical'),
        ('Évaluation', 'Évaluation'),
        ('Mixte', 'Mixte')
    ])
    
    date = DateField('Date', validators=[
        DataRequired(message='La date est obligatoire')
    ])
    
    start_time = TimeField('Heure de début', validators=[Optional()])
    
    duration = IntegerField('Durée (minutes)', validators=[
        DataRequired(message='La durée est obligatoire'),
        NumberRange(min=15, max=300)
    ])
    
    team_id = SelectField('Équipe', coerce=int, validators=[Optional()])
    
    description = TextAreaField('Description', validators=[Optional()])
    objectives = TextAreaField('Objectifs', validators=[Optional()])
    
    target_load = FloatField('Charge cible', validators=[Optional()])
    target_distance = FloatField('Distance cible (km)', validators=[Optional()])
    
    submit = SubmitField('Enregistrer')


# =============================================================================
# FORMULAIRES RÉSULTATS / PERFORMANCES
# =============================================================================

class ResultForm(FlaskForm):
    """Formulaire de saisie des résultats"""
    
    player_id = SelectField('Joueur', coerce=int, validators=[
        DataRequired(message='Sélectionnez un joueur')
    ])
    
    rpe = IntegerField('RPE (1-10)', validators=[
        Optional(),
        NumberRange(min=1, max=10, message='La valeur doit être entre 1 et 10')
    ])
    
    technical_rating = FloatField('Note technique (1-10)', validators=[
        Optional(),
        NumberRange(min=1, max=10)
    ])
    
    tactical_rating = FloatField('Note tactique (1-10)', validators=[
        Optional(),
        NumberRange(min=1, max=10)
    ])
    
    notes = TextAreaField('Remarques', validators=[Optional()])
    
    submit = SubmitField('Enregistrer')


class QuickResultForm(FlaskForm):
    """Formulaire rapide pour saisie en masse"""
    
    rpe = IntegerField('RPE', validators=[
        Optional(),
        NumberRange(min=1, max=10)
    ])
    
    technical_rating = FloatField('Technique', validators=[
        Optional(),
        NumberRange(min=1, max=10)
    ])


# =============================================================================
# FORMULAIRES GPS
# =============================================================================

class GPSUploadForm(FlaskForm):
    """Formulaire d'upload de fichier GPS"""
    
    file = FileField('Fichier GPS', validators=[
        DataRequired(message='Sélectionnez un fichier'),
        FileAllowed(['csv', 'xlsx', 'xls', 'json', 'xml'], 
                    message='Formats acceptés : CSV, Excel, JSON, XML')
    ])
    
    provider = SelectField('Fournisseur GPS', choices=[
        ('Catapult', 'Catapult'),
        ('STATSports', 'STATSports (Apex)'),
        ('Playertek', 'Playertek'),
        ('GPExe', 'GPExe'),
        ('Polar', 'Polar Team Pro'),
        ('Kinexon', 'Kinexon'),
        ('Autre', 'Autre')
    ])
    
    session_id = SelectField('Séance associée', coerce=int, validators=[
        DataRequired(message='Sélectionnez une séance')
    ])
    
    submit = SubmitField('Importer')


# =============================================================================
# FORMULAIRES WELLNESS
# =============================================================================

class WellnessForm(FlaskForm):
    """Formulaire de bien-être quotidien"""
    
    fatigue = SelectField('Niveau de fatigue', choices=[
        (5, '5 - Très frais'),
        (4, '4 - Frais'),
        (3, '3 - Normal'),
        (2, '2 - Fatigué'),
        (1, '1 - Très fatigué')
    ], coerce=int)
    
    sleep_quality = SelectField('Qualité du sommeil', choices=[
        (5, '5 - Excellent'),
        (4, '4 - Bon'),
        (3, '3 - Moyen'),
        (2, '2 - Mauvais'),
        (1, '1 - Très mauvais')
    ], coerce=int)
    
    sleep_hours = FloatField('Heures de sommeil', validators=[
        Optional(),
        NumberRange(min=0, max=24)
    ])
    
    muscle_soreness = SelectField('Douleurs musculaires', choices=[
        (5, '5 - Aucune douleur'),
        (4, '4 - Légères'),
        (3, '3 - Modérées'),
        (2, '2 - Importantes'),
        (1, '1 - Très douloureuses')
    ], coerce=int)
    
    stress = SelectField('Niveau de stress', choices=[
        (5, '5 - Très détendu'),
        (4, '4 - Détendu'),
        (3, '3 - Normal'),
        (2, '2 - Stressé'),
        (1, '1 - Très stressé')
    ], coerce=int)
    
    mood = SelectField('Humeur', choices=[
        (5, '5 - Excellent'),
        (4, '4 - Bon'),
        (3, '3 - Neutre'),
        (2, '2 - Mauvais'),
        (1, '1 - Très mauvais')
    ], coerce=int)
    
    hr_rest = IntegerField('FC au repos (bpm)', validators=[
        Optional(),
        NumberRange(min=30, max=120)
    ])
    
    weight = FloatField('Poids (kg)', validators=[
        Optional(),
        NumberRange(min=30, max=150)
    ])
    
    notes = TextAreaField('Notes', validators=[Optional()])
    
    submit = SubmitField('Enregistrer')


# =============================================================================
# FORMULAIRES BLESSURES
# =============================================================================

class InjuryForm(FlaskForm):
    """Formulaire de blessure"""
    
    player_id = SelectField('Joueur', coerce=int, validators=[
        DataRequired(message='Sélectionnez un joueur')
    ])
    
    injury_type = SelectField('Type de blessure', choices=[
        ('Entorse', 'Entorse'),
        ('Élongation', 'Élongation'),
        ('Claquage', 'Claquage'),
        ('Contusion', 'Contusion'),
        ('Fracture', 'Fracture'),
        ('Tendinite', 'Tendinite'),
        ('Pubalgie', 'Pubalgie'),
        ('Lombalgie', 'Lombalgie'),
        ('Commotion', 'Commotion'),
        ('Autre', 'Autre')
    ])
    
    body_part = SelectField('Partie du corps', choices=[
        ('Cheville', 'Cheville'),
        ('Genou', 'Genou'),
        ('Cuisse', 'Cuisse'),
        ('Mollet', 'Mollet'),
        ('Hanche', 'Hanche'),
        ('Dos', 'Dos'),
        ('Épaule', 'Épaule'),
        ('Tête', 'Tête'),
        ('Pied', 'Pied'),
        ('Autre', 'Autre')
    ])
    
    severity = SelectField('Gravité', choices=[
        ('Légère', 'Légère'),
        ('Modérée', 'Modérée'),
        ('Grave', 'Grave')
    ])
    
    date_injury = DateField('Date de la blessure', validators=[
        DataRequired(message='La date est obligatoire')
    ])
    
    expected_return = DateField('Retour prévu', validators=[Optional()])
    
    mechanism = StringField('Mécanisme', validators=[Optional()])
    
    context = SelectField('Contexte', choices=[
        ('Entraînement', 'Entraînement'),
        ('Match', 'Match'),
        ('Autre', 'Autre')
    ])
    
    treatment = TextAreaField('Traitement', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    
    submit = SubmitField('Enregistrer')


# =============================================================================
# FORMULAIRES FILTRES
# =============================================================================

class FilterForm(FlaskForm):
    """Formulaire de filtrage générique"""
    
    team_id = SelectField('Équipe', coerce=int, validators=[Optional()])
    session_type = SelectField('Type de séance', validators=[Optional()])
    date_from = DateField('Du', validators=[Optional()])
    date_to = DateField('Au', validators=[Optional()])
    status = SelectField('Statut', validators=[Optional()])


# =============================================================================
# RESET PASSWORD (Etape 2 - Securite)
# =============================================================================

class ForgotPasswordForm(FlaskForm):
    """Demande de reinitialisation du mot de passe."""
    email = EmailField('Email', validators=[
        DataRequired(message='L\'email est obligatoire'),
        Email(message='Email invalide')
    ])
    submit = SubmitField('Envoyer le lien de reinitialisation')


class ResetPasswordForm(FlaskForm):
    """Definition d'un nouveau mot de passe."""
    password = PasswordField('Nouveau mot de passe', validators=[
        DataRequired(message='Le mot de passe est obligatoire'),
        Length(min=8, message='Le mot de passe doit faire au moins 8 caracteres')
    ])
    password2 = PasswordField('Confirmer le mot de passe', validators=[
        DataRequired(message='La confirmation est obligatoire'),
        EqualTo('password', message='Les mots de passe ne correspondent pas')
    ])
    submit = SubmitField('Reinitialiser')
