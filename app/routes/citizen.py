from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.shelter import Shelter
from app.models.beneficiary import Beneficiary
from app.models.shelter_registration import ShelterRegistrationRequest
from app.utils import role_required, active_required
from app.services.notification_service import notify_role
from app.services.telegram_api import build_inline_keyboard

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
    shelters = Shelter.query.filter_by(status='active').all()
    profile = Beneficiary.query.filter_by(user_id=current_user.id).first()
    pending_requests = ShelterRegistrationRequest.query.filter_by(
        citizen_user_id=current_user.id,
        status='pending'
    ).all()
    return render_template('citizen/dashboard.html', shelters=shelters, profile=profile, pending_requests=pending_requests)


@citizen_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@role_required('citizen')
def profile():
    profile = Beneficiary.query.filter_by(user_id=current_user.id).first()
    if request.method == 'POST':
        identification_number = request.form.get('identification_number')
        full_name = request.form.get('full_name')
        phone_number = request.form.get('phone_number')
        address = request.form.get('address')

        if not profile:
            profile = Beneficiary(
                user_id=current_user.id,
                identification_number=identification_number,
                full_name=full_name,
                is_verified=False
            )
            db.session.add(profile)
        else:
            profile.identification_number = identification_number
            profile.full_name = full_name
            profile.is_verified = False

        profile.user_id = current_user.id
        db.session.commit()
        flash('Your profile data has been submitted for government verification.', 'success')
        return redirect(url_for('citizen.dashboard'))

    return render_template('citizen/profile.html', profile=profile)


@citizen_bp.route('/shelter/request', methods=['GET', 'POST'])
@login_required
@role_required('citizen')
def shelter_request():
    shelters = Shelter.query.filter_by(status='active').all()
    if request.method == 'POST':
        shelter_id = request.form.get('shelter_id')
        full_name = request.form.get('full_name')
        identification_number = request.form.get('identification_number')
        phone_number = request.form.get('phone_number')
        address = request.form.get('address')
        notes = request.form.get('notes')

        shelter = Shelter.query.get_or_404(shelter_id)
        request_entry = ShelterRegistrationRequest(
            citizen_user_id=current_user.id,
            shelter_id=shelter.id,
            full_name=full_name or current_user.username,
            identification_number=identification_number,
            phone_number=phone_number,
            address=address,
            notes=notes,
            status='pending',
            created_by_role='citizen',
            created_by_id=current_user.id
        )
        db.session.add(request_entry)
        db.session.commit()
        notify_role('gov_officer', f'New shelter registration request from {request_entry.full_name} '
                                    f'for {shelter.shelter_name}.',
                    title='New registration request', urgency='info',
                    reply_markup=build_inline_keyboard([[
                        ('✅ Approve', f'apr_reg:{request_entry.id}'),
                        ('❌ Reject', f'rej_reg:{request_entry.id}'),
                    ]]))
        flash('Your shelter registration request has been submitted for review.', 'success')
        return redirect(url_for('citizen.dashboard'))

    return render_template('citizen/request_shelter.html', shelters=shelters)