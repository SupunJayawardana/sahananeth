from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.shelter import Shelter
from app.models.beneficiary import Beneficiary
from app.models.shelter_registration import ShelterRegistrationRequest
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
    flash(f'Shelter "{shelter.shelter_name}" has been rejected.', 'danger')
    return redirect(url_for('gov.dashboard'))

@gov_bp.route('/procurement')
@login_required
@role_required('gov_officer')
@active_required
def procurement_requests():
    from app.models.procurement import ProcurementRequest
    from app.models.warehouse import Warehouse
    requests = ProcurementRequest.query.order_by(
        ProcurementRequest.created_at.desc()
    ).all()
    warehouses = Warehouse.query.all()
    return render_template('gov_officer/procurement.html',
                           requests=requests,
                           warehouses=warehouses)


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


@gov_bp.route('/registrations/approve/<int:request_id>')
@login_required
@role_required('gov_officer')
@active_required
def approve_registration(request_id):
    registration = ShelterRegistrationRequest.query.get_or_404(request_id)
    registration.status = 'approved'
    registration.reviewed_by_id = current_user.id
    registration.reviewed_at = db.func.now()

    beneficiary = Beneficiary.query.filter_by(identification_number=registration.identification_number).first()
    if beneficiary:
        beneficiary.is_verified = True
        beneficiary.allocated_shelter_id = registration.shelter_id
    else:
        beneficiary = Beneficiary(
            identification_number=registration.identification_number,
            full_name=registration.full_name,
            is_verified=True,
            allocated_shelter_id=registration.shelter_id
        )
        db.session.add(beneficiary)

    db.session.commit()
    flash('Registration request approved and beneficiary profile verified.', 'success')
    return redirect(url_for('gov.dashboard'))


@gov_bp.route('/registrations/reject/<int:request_id>')
@login_required
@role_required('gov_officer')
@active_required
def reject_registration(request_id):
    registration = ShelterRegistrationRequest.query.get_or_404(request_id)
    registration.status = 'rejected'
    registration.reviewed_by_id = current_user.id
    registration.reviewed_at = db.func.now()
    db.session.commit()
    flash('Registration request rejected.', 'danger')
    return redirect(url_for('gov.dashboard'))