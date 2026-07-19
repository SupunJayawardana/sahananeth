from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.shelter import Shelter
from app.models.beneficiary import Beneficiary
from app.models.shelter_registration import ShelterRegistrationRequest
from app.utils import role_required, active_required
from app.services.activity_service import log_activity
from app.services.notification_service import notify_user, notify_role

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
    pending_shelters = Shelter.query.filter_by(status='pending_approval').all()
    pending_registrations = ShelterRegistrationRequest.query.filter_by(status='pending').all()
    return render_template('gov_officer/dashboard.html',
                           pending_field_officers=pending_field_officers,
                           pending_shelters=pending_shelters,
                           pending_registrations=pending_registrations)


@gov_bp.route('/approve/field-officer/<int:user_id>')
@login_required
@role_required('gov_officer')
@active_required
def approve_field_officer(user_id):
    user = User.query.get_or_404(user_id)
    if user.role_level != 'field_officer':
        flash('You can only approve Field Officers.', 'danger')
        return redirect(url_for('gov.dashboard'))
    user.status = 'active'
    db.session.commit()
    log_activity('user', f'Field Officer {user.username} approved by {current_user.username}.', user_id=current_user.id)
    notify_user(user, 'Your Field Officer account has been approved. You can now log in.',
                title='Account approved', urgency='info')
    flash(f'{user.username} has been approved as Field Officer.', 'success')
    return redirect(url_for('gov.dashboard'))


@gov_bp.route('/reject/field-officer/<int:user_id>')
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
    log_activity('user', f'Field Officer {user.username} rejected by {current_user.username}.', user_id=current_user.id)
    notify_user(user, 'Your Field Officer account application has been rejected.',
                title='Account rejected', urgency='warning')
    flash(f'{user.username} has been rejected.', 'danger')
    return redirect(url_for('gov.dashboard'))


@gov_bp.route('/approve/shelter/<int:shelter_id>')
@login_required
@role_required('gov_officer')
@active_required
def approve_shelter(shelter_id):
    shelter = Shelter.query.get_or_404(shelter_id)
    shelter.status = 'active'
    shelter.approved_by_id = current_user.id
    db.session.commit()
    log_activity('shelter', f'Shelter "{shelter.shelter_name}" approved by {current_user.username}.', user_id=current_user.id)
    notify_user(shelter.created_by, f'Your shelter "{shelter.shelter_name}" has been approved and is now active.',
                title='Shelter approved', urgency='info')
    flash(f'Shelter "{shelter.shelter_name}" has been approved.', 'success')
    return redirect(url_for('gov.dashboard'))


@gov_bp.route('/reject/shelter/<int:shelter_id>')
@login_required
@role_required('gov_officer')
@active_required
def reject_shelter(shelter_id):
    shelter = Shelter.query.get_or_404(shelter_id)
    shelter.status = 'inactive'
    db.session.commit()
    log_activity('shelter', f'Shelter "{shelter.shelter_name}" rejected by {current_user.username}.', user_id=current_user.id)
    notify_user(shelter.created_by, f'Your shelter "{shelter.shelter_name}" was not approved.',
                title='Shelter rejected', urgency='warning')
    flash(f'Shelter "{shelter.shelter_name}" has been rejected.', 'danger')
    return redirect(url_for('gov.dashboard'))

@gov_bp.route('/procurement')
@login_required
@role_required('gov_officer')
@active_required
def procurement_requests():
    from app.models.procurement import ProcurementRequest
    from app.models.warehouse import Warehouse
    from app.services.geo_services import find_matching_warehouses
    import json

    requests = ProcurementRequest.query.order_by(
        ProcurementRequest.created_at.desc()
    ).all()

    # Pre-calculate GIS matches for each pending request
    gis_matches = {}
    for req in requests:
        if req.status_state == 'pending' and req.shelter:
            matches = find_matching_warehouses(
                req.shelter,
                req.requested_sku,
                req.quantity_needed
            )
            gis_matches[req.id] = matches

    warehouses = Warehouse.query.filter_by(status='active').all()

    return render_template('gov_officer/procurement.html',
                           requests=requests,
                           warehouses=warehouses,
                           gis_matches=gis_matches)


@gov_bp.route('/procurement/approve/<int:request_id>', methods=['POST'])
@login_required
@role_required('gov_officer')
@active_required
def approve_procurement(request_id):
    from app.models.procurement import ProcurementRequest
    from app.models.warehouse import Warehouse
    proc = ProcurementRequest.query.get_or_404(request_id)
    warehouse_id = request.form.get('warehouse_id')

    proc.status_state = 'approved'
    proc.fulfilled_warehouse_id = int(warehouse_id)
    db.session.commit()
    log_activity('procurement', f'Procurement request #{proc.id} ({proc.requested_sku}) approved by {current_user.username}.', user_id=current_user.id)
    notify_user(proc.requested_by,
                f'Your request for {proc.quantity_needed} {proc.metric_unit} of {proc.requested_sku} has been approved.',
                title='Procurement approved', urgency='info')
    for a in proc.fulfilled_warehouse.assignments:
        notify_user(a.user,
                    f'New dispatch task: {proc.quantity_needed} {proc.metric_unit} of {proc.requested_sku} '
                    f'for {proc.shelter.shelter_name}.',
                    title='New dispatch task', urgency='warning')
    flash('Procurement request approved and warehouse assigned.', 'success')
    return redirect(url_for('gov.procurement_requests'))


@gov_bp.route('/procurement/reject/<int:request_id>')
@login_required
@role_required('gov_officer')
@active_required
def reject_procurement(request_id):
    from app.models.procurement import ProcurementRequest
    proc = ProcurementRequest.query.get_or_404(request_id)
    proc.status_state = 'rejected'
    db.session.commit()
    log_activity('procurement', f'Procurement request #{proc.id} ({proc.requested_sku}) rejected by {current_user.username}.', user_id=current_user.id)
    notify_user(proc.requested_by,
                f'Your request for {proc.quantity_needed} {proc.metric_unit} of {proc.requested_sku} was rejected.',
                title='Procurement rejected', urgency='warning')
    flash('Procurement request rejected.', 'danger')
    return redirect(url_for('gov.procurement_requests'))

@gov_bp.route('/warehouse-managers')
@login_required
@role_required('gov_officer')
@active_required
def warehouse_managers():
    from app.models.warehouse_assignment import WarehouseAssignment
    from app.models.warehouse import Warehouse
    pending_wm = User.query.filter_by(
        role_level='warehouse_manager',
        status='pending'
    ).all()
    active_wm = User.query.filter_by(
        role_level='warehouse_manager',
        status='active'
    ).all()
    warehouses = Warehouse.query.all()
    return render_template('gov_officer/warehouse_managers.html',
                           pending_wm=pending_wm,
                           active_wm=active_wm,
                           warehouses=warehouses)


@gov_bp.route('/approve/warehouse-manager/<int:user_id>', methods=['POST'])
@login_required
@role_required('gov_officer')
@active_required
def approve_warehouse_manager(user_id):
    from app.models.warehouse_assignment import WarehouseAssignment
    user = User.query.get_or_404(user_id)
    warehouse_ids = request.form.getlist('warehouse_ids')

    if len(warehouse_ids) > 3:
        flash('A warehouse manager can be assigned to maximum 3 warehouses.', 'danger')
        return redirect(url_for('gov.warehouse_managers'))

    user.status = 'active'

    for wid in warehouse_ids:
        existing = WarehouseAssignment.query.filter_by(
            user_id=user.id,
            warehouse_id=int(wid)
        ).first()
        if not existing:
            assignment = WarehouseAssignment(
                user_id=user.id,
                warehouse_id=int(wid),
                assigned_by_id=current_user.id
            )
            db.session.add(assignment)

    db.session.commit()
    log_activity('user', f'Warehouse Manager {user.username} approved by {current_user.username}.', user_id=current_user.id)
    notify_user(user, 'Your Warehouse Manager account has been approved. You can now log in.',
                title='Account approved', urgency='info')
    flash(f'{user.username} approved and assigned to warehouses.', 'success')
    return redirect(url_for('gov.warehouse_managers'))


@gov_bp.route('/reject/warehouse-manager/<int:user_id>')
@login_required
@role_required('gov_officer')
@active_required
def reject_warehouse_manager(user_id):
    user = User.query.get_or_404(user_id)
    user.status = 'rejected'
    db.session.commit()
    log_activity('user', f'Warehouse Manager {user.username} rejected by {current_user.username}.', user_id=current_user.id)
    notify_user(user, 'Your Warehouse Manager account application has been rejected.',
                title='Account rejected', urgency='warning')
    flash(f'{user.username} has been rejected.', 'danger')
    return redirect(url_for('gov.warehouse_managers'))

# ─── Warehouse Management ────────────────────────────────────────────────────

@gov_bp.route('/warehouses')
@login_required
@role_required('gov_officer')
@active_required
def warehouses():
    from app.models.warehouse import Warehouse
    from app.models.warehouse_assignment import WarehouseAssignment
    from app.models.user import User
    active_warehouses = Warehouse.query.filter_by(status='active').all()
    pending_warehouses = Warehouse.query.filter_by(status='pending_approval').all()
    warehouse_managers = User.query.filter_by(
        role_level='warehouse_manager', status='active'
    ).all()
    all_warehouses = Warehouse.query.filter_by(status='active').all()
    return render_template('gov_officer/warehouses.html',
                           active_warehouses=active_warehouses,
                           pending_warehouses=pending_warehouses,
                           warehouse_managers=warehouse_managers,
                           all_warehouses=all_warehouses)


@gov_bp.route('/warehouses/create', methods=['POST'])
@login_required
@role_required('gov_officer')
@active_required
def create_warehouse():
    from app.models.warehouse import Warehouse
    warehouse_name = request.form.get('warehouse_name')
    address = request.form.get('address')
    lat = request.form.get('latitude')
    lng = request.form.get('longitude')

    warehouse = Warehouse(
        warehouse_name=warehouse_name,
        address=address,
        latitude=float(lat) if lat else None,
        longitude=float(lng) if lng else None,
        status='active',
        created_by_id=current_user.id,
        approved_by_id=current_user.id
    )
    db.session.add(warehouse)
    db.session.commit()
    log_activity('warehouse', f'Warehouse "{warehouse_name}" created by {current_user.username}.', user_id=current_user.id)
    flash(f'Warehouse "{warehouse_name}" created successfully.', 'success')
    return redirect(url_for('gov.warehouses'))


@gov_bp.route('/warehouses/approve/<int:warehouse_id>')
@login_required
@role_required('gov_officer')
@active_required
def approve_warehouse(warehouse_id):
    from app.models.warehouse import Warehouse
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    warehouse.status = 'active'
    warehouse.approved_by_id = current_user.id
    db.session.commit()
    log_activity('warehouse', f'Warehouse "{warehouse.warehouse_name}" approved by {current_user.username}.', user_id=current_user.id)
    notify_user(warehouse.created_by, f'Your warehouse "{warehouse.warehouse_name}" has been approved and is now active.',
                title='Warehouse approved', urgency='info')
    flash(f'Warehouse "{warehouse.warehouse_name}" approved.', 'success')
    return redirect(url_for('gov.warehouses'))


@gov_bp.route('/warehouses/reject/<int:warehouse_id>')
@login_required
@role_required('gov_officer')
@active_required
def reject_warehouse(warehouse_id):
    from app.models.warehouse import Warehouse
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    warehouse.status = 'inactive'
    db.session.commit()
    log_activity('warehouse', f'Warehouse "{warehouse.warehouse_name}" rejected by {current_user.username}.', user_id=current_user.id)
    notify_user(warehouse.created_by, f'Your warehouse "{warehouse.warehouse_name}" was not approved.',
                title='Warehouse rejected', urgency='warning')
    flash(f'Warehouse "{warehouse.warehouse_name}" rejected.', 'danger')
    return redirect(url_for('gov.warehouses'))


@gov_bp.route('/warehouses/assign-manager', methods=['POST'])
@login_required
@role_required('gov_officer')
@active_required
def assign_warehouse_manager():
    from app.models.warehouse_assignment import WarehouseAssignment
    user_id = int(request.form.get('user_id'))
    warehouse_ids = request.form.getlist('warehouse_ids')

    # Check max 3 warehouses per manager
    existing_count = WarehouseAssignment.query.filter_by(user_id=user_id).count()
    if existing_count + len(warehouse_ids) > 3:
        flash('A warehouse manager can be assigned to maximum 3 warehouses.', 'danger')
        return redirect(url_for('gov.warehouses'))

    for wid in warehouse_ids:
        existing = WarehouseAssignment.query.filter_by(
            user_id=user_id,
            warehouse_id=int(wid)
        ).first()
        if not existing:
            assignment = WarehouseAssignment(
                user_id=user_id,
                warehouse_id=int(wid),
                assigned_by_id=current_user.id
            )
            db.session.add(assignment)

    db.session.commit()
    flash('Warehouse manager assigned successfully.', 'success')
    return redirect(url_for('gov.warehouses'))


@gov_bp.route('/aid-requests')
@login_required
@role_required('gov_officer')
@active_required
def aid_requests():
    """
    Previously CitizenAidRequest had NO web route or template anywhere —
    it was created only by the bot's /requestaid flow and could only be
    triaged via the two Telegram inline buttons. A Gov Officer who wasn't
    on Telegram, or who lost the message, had no way to ever see it again.
    """
    from app.models.citizen_aid_request import CitizenAidRequest
    status_filter = request.args.get('status', 'open')  # open | resolved | all
    query = CitizenAidRequest.query
    if status_filter == 'open':
        query = query.filter(CitizenAidRequest.status.in_(['pending', 'in_progress']))
    elif status_filter == 'resolved':
        query = query.filter(CitizenAidRequest.status == 'resolved')
    requests = query.order_by(CitizenAidRequest.created_at.desc()).all()
    return render_template('gov_officer/aid_requests.html', requests=requests, status_filter=status_filter)


@gov_bp.route('/aid-requests/<int:aid_id>/in-progress', methods=['POST'])
@login_required
@role_required('gov_officer')
@active_required
def aid_request_in_progress(aid_id):
    from app.services import approval_service
    ok, message = approval_service.mark_aid_in_progress(aid_id, current_user)
    flash(message, 'success' if ok else 'danger')
    return redirect(url_for('gov.aid_requests'))


@gov_bp.route('/aid-requests/<int:aid_id>/resolve', methods=['POST'])
@login_required
@role_required('gov_officer')
@active_required
def aid_request_resolve(aid_id):
    from app.services import approval_service
    ok, message = approval_service.mark_aid_resolved(aid_id, current_user)
    flash(message, 'success' if ok else 'danger')
    return redirect(url_for('gov.aid_requests'))


@gov_bp.route('/beneficiaries')
@login_required
@role_required('gov_officer')
@active_required
def beneficiaries():
    from app.services.beneficiary_service import search_and_filter
    q = request.args.get('q', '').strip()
    verified = request.args.get('verified', '')
    results = search_and_filter(q=q, verified=verified)
    return render_template('gov_officer/beneficiaries.html', results=results, q=q, verified=verified)


@gov_bp.route('/registrations/approve/<int:request_id>')
@login_required
@role_required('gov_officer')
@active_required
def approve_registration(request_id):
    # Delegates to approval_service so the web button and the Telegram
    # inline button run the exact same logic — this used to be
    # reimplemented here and had drifted (it never linked the new
    # Beneficiary back to registration.citizen_user_id, so a citizen who
    # self-submitted from the website and got approved from the website
    # ended up "verified" with no way for their own dashboard to find it).
    from app.services import approval_service
    ok, message = approval_service.approve_registration(request_id, current_user)
    flash(message, 'success' if ok else 'danger')
    return redirect(url_for('gov.dashboard'))


@gov_bp.route('/registrations/reject/<int:request_id>')
@login_required
@role_required('gov_officer')
@active_required
def reject_registration(request_id):
    from app.services import approval_service
    ok, message = approval_service.reject_registration(request_id, current_user)
    flash(message, 'danger' if ok else 'warning')
    return redirect(url_for('gov.dashboard'))