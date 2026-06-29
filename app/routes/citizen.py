from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User
from app.utils import role_required, active_required

citizen_bp = Blueprint('citizen', __name__)


@citizen_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('citizen.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return redirect(url_for('citizen.register'))

        new_user = User(
            username=username,
            role_level='citizen',
            status='active'         # Citizens active immediately
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)        # Auto login after register
        flash('Welcome to SAHANANETH!', 'success')
        return redirect(url_for('citizen.dashboard'))

    return render_template('citizen/register.html')


@citizen_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('citizen.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username, role_level='citizen').first()

        if not user or not user.check_password(password):
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('citizen.login'))

        login_user(user)
        return redirect(url_for('citizen.dashboard'))

    return render_template('citizen/login.html')


@citizen_bp.route('/dashboard')
@login_required
@role_required('citizen')
def dashboard():
    return render_template('citizen/dashboard.html')