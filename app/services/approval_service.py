"""
approval_service.py
--------------------
Backs the inline Approve/Reject buttons sent in Telegram messages (Phase 3).

Deliberately separate from the existing web routes rather than refactoring
them to share code — the web routes are already tested and working, and
each function here is a small, self-contained mirror of the equivalent
web action. Every function returns (success: bool, result_text: str);
result_text is what gets shown back in the edited Telegram message.

Each function re-checks the record's current status before acting, so
double-tapping a button (or a second person actioning the same item from
a different chat) is always safe — it never applies the same transition
twice, it just reports what's already true.
"""
from app.extensions import db
from app.services.activity_service import log_activity
from app.services.notification_service import notify_user

APPROVER_ROLES = {'gov_officer', 'super_admin'}
TRIAGE_ROLES = {'field_officer', 'gov_officer', 'super_admin'}


def _actor_allowed(actor, allowed_roles):
    return actor is not None and actor.role_level in allowed_roles


# ─── Staff account approval (Field Officer / Gov Officer / Warehouse Manager) ──

def approve_staff_user(user_id, actor):
    from app.models.user import User
    if not _actor_allowed(actor, APPROVER_ROLES):
        return False, 'Not authorized.'
    user = User.query.get(user_id)
    if not user:
        return False, 'Account no longer exists.'
    if user.status != 'pending':
        return False, f'Already handled — current status: {user.status}.'

    user.status = 'active'
    db.session.commit()
    log_activity('user', f'{user.username} ({user.role_level}) approved by {actor.username} via Telegram.', user_id=actor.id)
    notify_user(user, f'Your {user.role_level.replace("_", " ").title()} account has been approved. You can now log in.',
                title='Account approved', urgency='info')

    extra = ''
    if user.role_level == 'warehouse_manager':
        extra = '\n\nNote: assign their warehouse(s) from the "Manage Users" page on the web dashboard.'
    return True, f'✅ Approved {user.username} ({user.role_level.replace("_", " ").title()}).{extra}'


def reject_staff_user(user_id, actor):
    from app.models.user import User
    if not _actor_allowed(actor, APPROVER_ROLES):
        return False, 'Not authorized.'
    user = User.query.get(user_id)
    if not user:
        return False, 'Account no longer exists.'
    if user.status != 'pending':
        return False, f'Already handled — current status: {user.status}.'

    user.status = 'rejected'
    db.session.commit()
    log_activity('user', f'{user.username} ({user.role_level}) rejected by {actor.username} via Telegram.', user_id=actor.id)
    notify_user(user, 'Your account application has been rejected. Contact an administrator for details.',
                title='Account rejected', urgency='warning')
    return True, f'❌ Rejected {user.username} ({user.role_level.replace("_", " ").title()}).'


# ─── Shelter approval ───────────────────────────────────────────────────────

def approve_shelter(shelter_id, actor):
    from app.models.shelter import Shelter
    if not _actor_allowed(actor, APPROVER_ROLES):
        return False, 'Not authorized.'
    shelter = Shelter.query.get(shelter_id)
    if not shelter:
        return False, 'Shelter no longer exists.'
    if shelter.status != 'pending_approval':
        return False, f'Already handled — current status: {shelter.status}.'

    shelter.status = 'active'
    shelter.approved_by_id = actor.id
    db.session.commit()
    log_activity('shelter', f'Shelter "{shelter.shelter_name}" approved by {actor.username} via Telegram.', user_id=actor.id)
    notify_user(shelter.created_by, f'Your shelter "{shelter.shelter_name}" has been approved and is now active.',
                title='Shelter approved', urgency='info')
    return True, f'✅ Approved shelter "{shelter.shelter_name}".'


def reject_shelter(shelter_id, actor):
    from app.models.shelter import Shelter
    if not _actor_allowed(actor, APPROVER_ROLES):
        return False, 'Not authorized.'
    shelter = Shelter.query.get(shelter_id)
    if not shelter:
        return False, 'Shelter no longer exists.'
    if shelter.status != 'pending_approval':
        return False, f'Already handled — current status: {shelter.status}.'

    shelter.status = 'inactive'
    db.session.commit()
    log_activity('shelter', f'Shelter "{shelter.shelter_name}" rejected by {actor.username} via Telegram.', user_id=actor.id)
    notify_user(shelter.created_by, f'Your shelter "{shelter.shelter_name}" was not approved.',
                title='Shelter rejected', urgency='warning')
    return True, f'❌ Rejected shelter "{shelter.shelter_name}".'


# ─── Warehouse approval ─────────────────────────────────────────────────────

def approve_warehouse(warehouse_id, actor):
    from app.models.warehouse import Warehouse
    if not _actor_allowed(actor, APPROVER_ROLES):
        return False, 'Not authorized.'
    warehouse = Warehouse.query.get(warehouse_id)
    if not warehouse:
        return False, 'Warehouse no longer exists.'
    if warehouse.status != 'pending_approval':
        return False, f'Already handled — current status: {warehouse.status}.'

    warehouse.status = 'active'
    warehouse.approved_by_id = actor.id
    db.session.commit()
    log_activity('warehouse', f'Warehouse "{warehouse.warehouse_name}" approved by {actor.username} via Telegram.', user_id=actor.id)
    notify_user(warehouse.created_by, f'Your warehouse "{warehouse.warehouse_name}" has been approved and is now active.',
                title='Warehouse approved', urgency='info')
    return True, f'✅ Approved warehouse "{warehouse.warehouse_name}".'


def reject_warehouse(warehouse_id, actor):
    from app.models.warehouse import Warehouse
    if not _actor_allowed(actor, APPROVER_ROLES):
        return False, 'Not authorized.'
    warehouse = Warehouse.query.get(warehouse_id)
    if not warehouse:
        return False, 'Warehouse no longer exists.'
    if warehouse.status != 'pending_approval':
        return False, f'Already handled — current status: {warehouse.status}.'

    warehouse.status = 'inactive'
    db.session.commit()
    log_activity('warehouse', f'Warehouse "{warehouse.warehouse_name}" rejected by {actor.username} via Telegram.', user_id=actor.id)
    notify_user(warehouse.created_by, f'Your warehouse "{warehouse.warehouse_name}" was not approved.',
                title='Warehouse rejected', urgency='warning')
    return True, f'❌ Rejected warehouse "{warehouse.warehouse_name}".'


# ─── Procurement approval (auto-assigns the best-matching warehouse) ───────

def approve_procurement_auto(request_id, actor):
    from app.models.procurement import ProcurementRequest
    from app.services.geo_services import find_matching_warehouses
    if not _actor_allowed(actor, APPROVER_ROLES):
        return False, 'Not authorized.'
    proc = ProcurementRequest.query.get(request_id)
    if not proc:
        return False, 'Request no longer exists.'
    if proc.status_state != 'pending':
        return False, f'Already handled — current status: {proc.status_state}.'

    matches = find_matching_warehouses(proc.shelter, proc.requested_sku, proc.quantity_needed)
    if not matches or not matches[0]['has_sufficient']:
        return False, ('⚠️ No warehouse currently has enough stock to auto-assign. '
                       'Please approve manually from the web dashboard so you can review the options.')

    warehouse = matches[0]['warehouse']
    proc.status_state = 'approved'
    proc.fulfilled_warehouse_id = warehouse.id
    db.session.commit()
    log_activity('procurement', f'Procurement request #{proc.id} ({proc.requested_sku}) approved by {actor.username} via Telegram, '
                                 f'auto-assigned to {warehouse.warehouse_name}.', user_id=actor.id)
    notify_user(proc.requested_by,
                f'Your request for {proc.quantity_needed} {proc.metric_unit} of {proc.requested_sku} has been approved.',
                title='Procurement approved', urgency='info')
    for a in warehouse.assignments:
        notify_user(a.user,
                    f'New dispatch task: {proc.quantity_needed} {proc.metric_unit} of {proc.requested_sku} '
                    f'for {proc.shelter.shelter_name}.',
                    title='New dispatch task', urgency='warning')
    return True, (f'✅ Approved request #{proc.id} — {proc.quantity_needed} {proc.metric_unit} of {proc.requested_sku}, '
                  f'assigned to {warehouse.warehouse_name}.')


def reject_procurement(request_id, actor):
    from app.models.procurement import ProcurementRequest
    if not _actor_allowed(actor, APPROVER_ROLES):
        return False, 'Not authorized.'
    proc = ProcurementRequest.query.get(request_id)
    if not proc:
        return False, 'Request no longer exists.'
    if proc.status_state != 'pending':
        return False, f'Already handled — current status: {proc.status_state}.'

    proc.status_state = 'rejected'
    db.session.commit()
    log_activity('procurement', f'Procurement request #{proc.id} ({proc.requested_sku}) rejected by {actor.username} via Telegram.', user_id=actor.id)
    notify_user(proc.requested_by,
                f'Your request for {proc.quantity_needed} {proc.metric_unit} of {proc.requested_sku} was rejected.',
                title='Procurement rejected', urgency='warning')
    return True, f'❌ Rejected request #{proc.id} ({proc.requested_sku}).'


# ─── Citizen shelter registration approval ─────────────────────────────────

def approve_registration(reg_id, actor):
    from app.models.shelter_registration import ShelterRegistrationRequest
    if not _actor_allowed(actor, APPROVER_ROLES):
        return False, 'Not authorized.'
    reg = ShelterRegistrationRequest.query.get(reg_id)
    if not reg:
        return False, 'Registration request no longer exists.'
    if reg.status != 'pending':
        return False, f'Already handled — current status: {reg.status}.'

    from app.models.beneficiary import Beneficiary
    reg.status = 'approved'
    reg.reviewed_by_id = actor.id
    if not Beneficiary.query.filter_by(identification_number=reg.identification_number).first():
        db.session.add(Beneficiary(
            identification_number=reg.identification_number,
            full_name=reg.full_name,
            is_verified=True,
            allocated_shelter_id=reg.shelter_id,
            user_id=reg.citizen_user_id,
        ))
    db.session.commit()
    log_activity('shelter', f'Citizen registration for "{reg.full_name}" approved by {actor.username} via Telegram.', user_id=actor.id)
    if reg.citizen:
        notify_user(reg.citizen, f'Your shelter registration at "{reg.shelter.shelter_name}" has been approved.',
                    title='Registration approved', urgency='info')
    return True, f'✅ Approved registration for "{reg.full_name}".'


def reject_registration(reg_id, actor):
    from app.models.shelter_registration import ShelterRegistrationRequest
    if not _actor_allowed(actor, APPROVER_ROLES):
        return False, 'Not authorized.'
    reg = ShelterRegistrationRequest.query.get(reg_id)
    if not reg:
        return False, 'Registration request no longer exists.'
    if reg.status != 'pending':
        return False, f'Already handled — current status: {reg.status}.'

    reg.status = 'rejected'
    reg.reviewed_by_id = actor.id
    db.session.commit()
    log_activity('shelter', f'Citizen registration for "{reg.full_name}" rejected by {actor.username} via Telegram.', user_id=actor.id)
    if reg.citizen:
        notify_user(reg.citizen, f'Your shelter registration at "{reg.shelter.shelter_name}" was not approved.',
                    title='Registration rejected', urgency='warning')
    return True, f'❌ Rejected registration for "{reg.full_name}".'


# ─── Citizen aid-request triage (pending → in_progress → resolved) ─────────

def mark_aid_in_progress(aid_id, actor):
    from app.models.citizen_aid_request import CitizenAidRequest
    if not _actor_allowed(actor, TRIAGE_ROLES):
        return False, 'Not authorized.'
    aid = CitizenAidRequest.query.get(aid_id)
    if not aid:
        return False, 'Request no longer exists.'
    if aid.status != 'pending':
        return False, f'Already handled — current status: {aid.status}.'

    aid.status = 'in_progress'
    aid.resolved_by_id = actor.id
    db.session.commit()
    log_activity('shelter', f'{actor.username} started following up on aid request #{aid.id} via Telegram.', user_id=actor.id)
    notify_user(aid.citizen, f'{actor.username} is following up on your request: "{aid.description[:60]}".',
                title='Update on your request', urgency='info')
    return True, f'🔄 Marked aid request #{aid.id} as in progress.'


def mark_aid_resolved(aid_id, actor):
    from app.models.citizen_aid_request import CitizenAidRequest
    from datetime import datetime
    if not _actor_allowed(actor, TRIAGE_ROLES):
        return False, 'Not authorized.'
    aid = CitizenAidRequest.query.get(aid_id)
    if not aid:
        return False, 'Request no longer exists.'
    if aid.status == 'resolved':
        return False, 'Already marked resolved.'

    aid.status = 'resolved'
    aid.resolved_by_id = actor.id
    aid.resolved_at = datetime.utcnow()
    db.session.commit()
    log_activity('shelter', f'{actor.username} resolved aid request #{aid.id} via Telegram.', user_id=actor.id)
    notify_user(aid.citizen, f'Your request has been resolved: "{aid.description[:60]}".',
                title='Request resolved', urgency='info')
    return True, f'✅ Marked aid request #{aid.id} as resolved.'
