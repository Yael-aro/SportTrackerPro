"""
SportTracker Pro - Routes Admin (Journal d'audit, etc.)
========================================================
"""

from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import db, AuditLog, User

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Decorateur : seuls les admins peuvent acceder a la route."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != 'admin':
            flash("Acces reserve aux administrateurs.", 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/audit-logs')
@admin_required
def audit_logs():
    """
    Affiche le journal d'audit avec filtres et pagination.
    """
    # Recuperer les filtres depuis l'URL
    action_filter = request.args.get('action', '').strip()
    user_filter = request.args.get('user', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 50

    # Construire la requete
    query = AuditLog.query.order_by(AuditLog.timestamp.desc())

    if action_filter:
        query = query.filter(AuditLog.action.like(f'%{action_filter}%'))

    if user_filter:
        query = query.filter(
            (AuditLog.user_email.like(f'%{user_filter}%')) |
            (AuditLog.target_name.like(f'%{user_filter}%'))
        )

    # Pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    logs = pagination.items

    # Statistiques rapides
    stats = {
        'total': AuditLog.query.count(),
        'login_success': AuditLog.query.filter_by(action='login_success').count(),
        'login_failed': AuditLog.query.filter_by(action='login_failed').count(),
        'login_with_2fa': AuditLog.query.filter_by(action='login_success_with_2fa').count(),
        '2fa_enabled': AuditLog.query.filter_by(action='2fa_enabled').count(),
        'password_resets': AuditLog.query.filter_by(action='password_reset_success').count(),
    }

    # Liste des actions distinctes pour le menu de filtre
    distinct_actions = [r[0] for r in db.session.query(AuditLog.action).distinct().all()]
    distinct_actions.sort()

    return render_template(
        'admin/audit_logs.html',
        logs=logs,
        pagination=pagination,
        stats=stats,
        distinct_actions=distinct_actions,
        action_filter=action_filter,
        user_filter=user_filter
    )
