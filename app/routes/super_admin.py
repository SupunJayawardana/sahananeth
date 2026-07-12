from flask_login import login_required, current_user
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.extensions import db
from app.models.user import User
from app.models.shelter import Shelter
from app.utils import role_required

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/dashboard')
@login_required
@role_required('super_admin')
def dashboard():
    pending_users = User.query.filter_by(status='pending').all()
    pending_shelters = Shelter.query.filter_by(status='pending_approval').all()
    return render_template('super_admin/dashboard.html',
                           pending_users=pending_users,
                           pending_shelters=pending_shelters)


@admin_bp.route('/approve/user/<int:user_id>')
@login_required
@role_required('super_admin')
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    user.status = 'active'
    db.session.commit()
    flash(f'{user.username} has been approved.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/reject/user/<int:user_id>')
@login_required
@role_required('super_admin')
def reject_user(user_id):
    user = User.query.get_or_404(user_id)
    user.status = 'rejected'
    db.session.commit()
    flash(f'{user.username} has been rejected.', 'danger')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/approve/shelter/<int:shelter_id>')
@login_required
@role_required('super_admin')
def approve_shelter(shelter_id):
    shelter = Shelter.query.get_or_404(shelter_id)
    shelter.status = 'active'
    shelter.approved_by_id = current_user.id
    db.session.commit()
    flash(f'Shelter "{shelter.shelter_name}" has been approved.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/reject/shelter/<int:shelter_id>')
@login_required
@role_required('super_admin')
def reject_shelter(shelter_id):
    shelter = Shelter.query.get_or_404(shelter_id)
    shelter.status = 'inactive'
    db.session.commit()
    flash(f'Shelter "{shelter.shelter_name}" has been rejected.', 'danger')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/procurement')
@login_required
@role_required('super_admin')
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


@admin_bp.route('/procurement/approve/<int:request_id>', methods=['POST'])
@login_required
@role_required('super_admin')
def approve_procurement(request_id):
    from app.models.procurement import ProcurementRequest
    proc = ProcurementRequest.query.get_or_404(request_id)
    warehouse_id = request.form.get('warehouse_id')
    proc.status_state = 'approved'
    proc.fulfilled_warehouse_id = int(warehouse_id)
    db.session.commit()
    flash('Procurement request approved.', 'success')
    return redirect(url_for('admin.procurement_requests'))


@admin_bp.route('/procurement/reject/<int:request_id>')
@login_required
@role_required('super_admin')
def reject_procurement(request_id):
    from app.models.procurement import ProcurementRequest
    proc = ProcurementRequest.query.get_or_404(request_id)
    proc.status_state = 'rejected'
    db.session.commit()
    flash('Procurement request rejected.', 'danger')
    return redirect(url_for('admin.procurement_requests'))

@admin_bp.route('/warehouses')
@login_required
@role_required('super_admin')
def warehouses():
    from app.models.warehouse import Warehouse
    from app.models.warehouse_assignment import WarehouseAssignment
    from app.models.user import User
    active_warehouses = Warehouse.query.filter_by(status='active').all()
    pending_warehouses = Warehouse.query.filter_by(status='pending_approval').all()
    warehouse_managers = User.query.filter_by(
        role_level='warehouse_manager', status='active'
    ).all()
    return render_template('gov_officer/warehouses.html',
                           active_warehouses=active_warehouses,
                           pending_warehouses=pending_warehouses,
                           warehouse_managers=warehouse_managers,
                           all_warehouses=active_warehouses)


@admin_bp.route('/warehouses/create', methods=['POST'])
@login_required
@role_required('super_admin')
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
    flash(f'Warehouse "{warehouse_name}" created.', 'success')
    return redirect(url_for('admin.warehouses'))


@admin_bp.route('/warehouses/approve/<int:warehouse_id>')
@login_required
@role_required('super_admin')
def approve_warehouse(warehouse_id):
    from app.models.warehouse import Warehouse
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    warehouse.status = 'active'
    warehouse.approved_by_id = current_user.id
    db.session.commit()
    flash(f'Warehouse "{warehouse.warehouse_name}" approved.', 'success')
    return redirect(url_for('admin.warehouses'))


@admin_bp.route('/warehouses/reject/<int:warehouse_id>')
@login_required
@role_required('super_admin')
def reject_warehouse(warehouse_id):
    from app.models.warehouse import Warehouse
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    warehouse.status = 'inactive'
    db.session.commit()
    flash(f'Warehouse "{warehouse.warehouse_name}" rejected.', 'danger')
    return redirect(url_for('admin.warehouses'))


@admin_bp.route('/warehouses/assign-manager', methods=['POST'])
@login_required
@role_required('super_admin')
def assign_warehouse_manager():
    from app.models.warehouse_assignment import WarehouseAssignment
    user_id = int(request.form.get('user_id'))
    warehouse_ids = request.form.getlist('warehouse_ids')

    existing_count = WarehouseAssignment.query.filter_by(user_id=user_id).count()
    if existing_count + len(warehouse_ids) > 3:
        flash('Maximum 3 warehouses per manager.', 'danger')
        return redirect(url_for('admin.warehouses'))

    for wid in warehouse_ids:
        existing = WarehouseAssignment.query.filter_by(
            user_id=user_id, warehouse_id=int(wid)
        ).first()
        if not existing:
            assignment = WarehouseAssignment(
                user_id=user_id,
                warehouse_id=int(wid),
                assigned_by_id=current_user.id
            )
            db.session.add(assignment)

    db.session.commit()
    flash('Manager assigned successfully.', 'success')
    return redirect(url_for('admin.warehouses'))