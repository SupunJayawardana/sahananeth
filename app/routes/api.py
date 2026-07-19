"""
api.py
------
Small JSON search endpoints backing the reusable "pick a person" widget
(see app/static/js/entity-picker.js). Previously every form that needed
to reference a citizen/beneficiary did it differently — most had no
search at all, just an exact-match check on submit, which is part of why
duplicate Beneficiary records could happen (a typo'd or partially-entered
ID wouldn't match, so a new record got created instead of the form
surfacing the near-match for a human to confirm).
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.utils import role_required

api_bp = Blueprint('api', __name__)

STAFF_ROLES = {'field_officer', 'gov_officer', 'super_admin', 'warehouse_manager'}


@api_bp.route('/lookup/beneficiaries')
@login_required
def lookup_beneficiaries():
    if current_user.role_level not in STAFF_ROLES:
        return jsonify({'results': []}), 403
    from app.services.citizen_service import search_beneficiaries
    q = request.args.get('q', '')
    results = search_beneficiaries(q, limit=10)
    return jsonify({'results': [
        {
            'id': b.id,
            'label': b.full_name,
            'sublabel': f"ID {b.identification_number}"
                        + (f" · {b.shelter.shelter_name}" if b.shelter else '')
                        + (' · verified' if b.is_verified else ' · unverified'),
            'identification_number': b.identification_number,
        }
        for b in results
    ]})


@api_bp.route('/lookup/users')
@login_required
def lookup_users():
    if current_user.role_level not in STAFF_ROLES:
        return jsonify({'results': []}), 403
    from app.models.user import User
    q = request.args.get('q', '').strip()
    role = request.args.get('role', '')
    if len(q) < 2:
        return jsonify({'results': []})
    query = User.query.filter(User.username.ilike(f'%{q}%') | User.full_name.ilike(f'%{q}%'))
    if role:
        query = query.filter(User.role_level == role)
    users = query.limit(10).all()
    return jsonify({'results': [
        {'id': u.id, 'label': u.full_name or u.username, 'sublabel': f'{u.role_level} · {u.status}'}
        for u in users
    ]})
