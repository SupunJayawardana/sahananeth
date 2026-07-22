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


@api_bp.route('/citizens/<int:user_id>/request-location', methods=['POST'])
@login_required
def request_citizen_location(user_id):
    """
    Asks the citizen — over Telegram — to share their actual current
    location, rather than a staff member guessing or substituting their
    own device's GPS. If an aid_request_id is given, the response also
    gets stamped onto that specific request once it comes in.
    """
    if current_user.role_level not in STAFF_ROLES:
        return jsonify({'error': 'Not authorized'}), 403

    from app.models.user import User
    from app.models.telegram_conversation_state import TelegramConversationState
    from app.services import telegram_api
    from app.extensions import db

    target = User.query.get_or_404(user_id)
    if target.role_level != 'citizen':
        return jsonify({'error': 'Location requests are only for citizen accounts'}), 400
    if not target.telegram_chat_id:
        return jsonify({'error': f'{target.full_name or target.username} has not connected Telegram, '
                                 f'so they can\'t be asked this way.'}), 400

    data = request.get_json(silent=True) or {}
    aid_request_id = data.get('aid_request_id')

    state = TelegramConversationState.query.filter_by(chat_id=target.telegram_chat_id).first()
    if not state:
        state = TelegramConversationState(chat_id=target.telegram_chat_id)
        db.session.add(state)
    state.flow_name = 'awaiting_location'
    state.step = 'waiting'
    state.set_data({'aid_request_id': aid_request_id, 'requested_by_id': current_user.id})

    ok, err = telegram_api.send_location_request(
        target.telegram_chat_id,
        f'Hi {target.full_name or target.username}, {current_user.full_name or current_user.username} '
        f'from SAHANANETH is asking for your current location to help respond faster. '
        f'Tap the button below to share it.'
    )
    if not ok:
        return jsonify({'error': f'Could not reach them on Telegram: {err}'}), 502

    db.session.commit()
    from app.services.activity_service import log_activity
    log_activity('user', f'{current_user.username} asked {target.full_name or target.username} to share their location.',
                 user_id=current_user.id)
    return jsonify({'ok': True})


@api_bp.route('/citizens/<int:user_id>/location', methods=['POST'])
@login_required
def set_citizen_location(user_id):
    """
    Lets staff confirm a citizen's location on their behalf — used by the
    location-picker widget on aid-request cards. Previously only the
    citizen's own browser "share my location" button could set this,
    which meant it stayed blank for anyone triaging a request from
    someone who never used that button (or a walk-in with no bot/website
    access at all).
    """
    if current_user.role_level not in STAFF_ROLES:
        return jsonify({'error': 'Not authorized'}), 403

    from app.models.user import User
    from app.extensions import db
    from app.services.activity_service import log_activity

    target = User.query.get_or_404(user_id)
    if target.role_level != 'citizen':
        return jsonify({'error': 'Location confirmation is only for citizen accounts'}), 400

    data = request.get_json(silent=True) or {}
    try:
        lat = float(data.get('lat'))
        lng = float(data.get('lng'))
    except (TypeError, ValueError):
        return jsonify({'error': 'lat and lng are required numbers'}), 400
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return jsonify({'error': 'lat/lng out of range'}), 400

    target.latitude = lat
    target.longitude = lng
    db.session.commit()
    log_activity('user', f'{current_user.username} confirmed location for {target.full_name or target.username}.',
                 user_id=current_user.id)

    return jsonify({'ok': True, 'lat': lat, 'lng': lng})
