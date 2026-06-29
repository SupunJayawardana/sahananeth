from flask import Blueprint, render_template
from flask_login import login_required
from app.utils import role_required, active_required
from app.models.user import User

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/dashboard')
@login_required
@role_required('super_admin')
def dashboard():
    pending_users = User.query.filter_by(status='pending').all()
    return render_template('super_admin/dashboard.html', pending_users=pending_users)


@admin_bp.route('/approve/<int:user_id>')
@login_required
@role_required('super_admin')
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    user.status = 'active'
    from app.extensions import db
    db.session.commit()
    from flask import flash, redirect, url_for
    flash(f'{user.username} has been approved.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/reject/<int:user_id>')
@login_required
@role_required('super_admin')
def reject_user(user_id):
    user = User.query.get_or_404(user_id)
    user.status = 'rejected'
    from app.extensions import db
    db.session.commit()
    from flask import flash, redirect, url_for
    flash(f'{user.username} has been rejected.', 'danger')
    return redirect(url_for('admin.dashboard'))