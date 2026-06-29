from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Staff login — for Gov Officer, Field Officer, Super Admin."""
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('auth.login'))

        # Block citizens from staff login
        if user.role_level == 'citizen':
            flash('Please use the Citizen login portal.', 'warning')
            return redirect(url_for('auth.login'))

        login_user(user)
        return redirect(url_for('auth.dashboard'))

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Staff registration — Gov Officer and Field Officer only."""
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        full_name = request.form.get('full_name')
        password = request.form.get('password')
        role = request.form.get('role')

        # Only allow staff roles here
        if role not in ('gov_officer', 'field_officer'):
            flash('Invalid role selected.', 'danger')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return redirect(url_for('auth.register'))

        new_user = User(
            username=username,
            full_name=full_name,
            role_level=role,
            status='pending'        # Always pending until approved
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration submitted. Please wait for approval before logging in.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/pending')
@login_required
def pending():
    """Shown to staff who are logged in but not yet approved."""
    return render_template('auth/pending.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/dashboard')
@login_required
def dashboard():
    """Central redirect — sends each role to their own dashboard."""
    if current_user.role_level == 'super_admin':
        return redirect(url_for('admin.dashboard'))
    elif current_user.role_level == 'gov_officer':
        if current_user.status == 'pending':
            return redirect(url_for('auth.pending'))
        return redirect(url_for('gov.dashboard'))
    elif current_user.role_level == 'field_officer':
        if current_user.status == 'pending':
            return redirect(url_for('auth.pending'))
        return redirect(url_for('field.dashboard'))
    else:
        return redirect(url_for('citizen.dashboard'))