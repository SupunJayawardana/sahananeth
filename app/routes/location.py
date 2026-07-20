from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.beneficiary import Beneficiary
from app.utils import role_required, active_required
from datetime import datetime

location_bp = Blueprint('location', __name__)


@location_bp.route('/update', methods=['POST'])
@login_required
def update_my_location():
    """Called from browser Geolocation API — updates current user's location."""
    data = request.get_json(silent=True) or {}
    try:
        lat = float(data.get('latitude'))
        lng = float(data.get('longitude'))
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'error': 'Invalid coordinates'}), 400

    current_user.latitude = lat
    current_user.longitude = lng
    current_user.location_updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True, 'latitude': lat, 'longitude': lng})


@location_bp.route('/beneficiary/<int:beneficiary_id>/update', methods=['POST'])
@login_required
@role_required('field_officer', 'gov_officer', 'super_admin')
@active_required
def update_beneficiary_location(beneficiary_id):
    """Field officer / Gov officer updates a beneficiary's location."""
    beneficiary = Beneficiary.query.get_or_404(beneficiary_id)
    data = request.get_json(silent=True) or {}
    try:
        lat = float(data.get('latitude'))
        lng = float(data.get('longitude'))
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'error': 'Invalid coordinates'}), 400

    beneficiary.latitude = lat
    beneficiary.longitude = lng
    beneficiary.location_updated_at = datetime.utcnow()
    beneficiary.location_verified = True
    db.session.commit()
    return jsonify({'ok': True, 'latitude': lat, 'longitude': lng})


@location_bp.route('/beneficiary/<int:beneficiary_id>/verify', methods=['POST'])
@login_required
@role_required('field_officer', 'gov_officer', 'super_admin')
@active_required
def verify_beneficiary_location(beneficiary_id):
    """Mark a beneficiary's location as verified."""
    beneficiary = Beneficiary.query.get_or_404(beneficiary_id)
    beneficiary.location_verified = True
    db.session.commit()
    return jsonify({'ok': True})


@location_bp.route('/map')
@login_required
@role_required('gov_officer', 'super_admin', 'field_officer')
@active_required
def location_map():
    """Full-screen map of all citizens, beneficiaries, shelters."""
    from app.models.shelter import Shelter
    shelters = Shelter.query.filter_by(status='active').all()
    users_with_location = User.query.filter(
        User.latitude.isnot(None),
        User.role_level == 'citizen'
    ).all()
    beneficiaries_with_location = Beneficiary.query.filter(
        Beneficiary.latitude.isnot(None)
    ).all()
    return render_template('shared/location_map.html',
                           shelters=shelters,
                           citizens=users_with_location,
                           beneficiaries=beneficiaries_with_location)