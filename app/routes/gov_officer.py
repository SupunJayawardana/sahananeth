from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from app.utils import role_required, active_required

gov_bp = Blueprint('gov', __name__)


@gov_bp.route('/dashboard')
@login_required
@role_required('gov_officer')
@active_required
def dashboard():
    pending_field_officers = User.query.filter_by(
        role_level='field_officer',
        status='pending'
    ).all()
    return render_template('gov_officer/dashboard.html',
                           pending_field_officers=pending_field_officers)


@gov_bp.route('/approve/<int:user_id>')
@login_required
@role_required('gov_officer')
@active_required
def approve_field_officer(user_id):
    user = User.query.get_or_404(user_id)

    # Gov officer can only approve field officers
    if user.role_level != 'field_officer':
        flash('You can only approve Field Officers.', 'danger')
        return redirect(url_for('gov.dashboard'))

    user.status = 'active'
    db.session.commit()
    flash(f'{user.username} has been approved as Field Officer.', 'success')
    return redirect(url_for('gov.dashboard'))


@gov_bp.route('/reject/<int:user_id>')
@login_required
@role_required('gov_officer')
@active_required
def reject_field_officer(user_id):
    user = User.query.get_or_404(user_id)

    if user.role_level != 'field_officer':
        flash('You can only reject Field Officers.', 'danger')
        return redirect(url_for('gov.dashboard'))

    user.status = 'rejected'
    db.session.commit()
    flash(f'{user.username} has been rejected.', 'danger')
    return redirect(url_for('gov.dashboard'))