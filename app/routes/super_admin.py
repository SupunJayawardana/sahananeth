from flask_login import login_required, current_user
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.extensions import db
from app.models.user import User
from app.models.shelter import Shelter
from app.utils import role_required
from app.services.activity_service import log_activity

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
    log_activity('user', f'{user.username} ({user.role_level}) approved by {current_user.username}.', user_id=current_user.id)
    flash(f'{user.username} has been approved.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/reject/user/<int:user_id>')
@login_required
@role_required('super_admin')
def reject_user(user_id):
    user = User.query.get_or_404(user_id)
    user.status = 'rejected'
    db.session.commit()
    log_activity('user', f'{user.username} ({user.role_level}) rejected by {current_user.username}.', user_id=current_user.id)
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
    log_activity('shelter', f'Shelter "{shelter.shelter_name}" approved by {current_user.username}.', user_id=current_user.id)
    flash(f'Shelter "{shelter.shelter_name}" has been approved.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/reject/shelter/<int:shelter_id>')
@login_required
@role_required('super_admin')
def reject_shelter(shelter_id):
    shelter = Shelter.query.get_or_404(shelter_id)
    shelter.status = 'inactive'
    db.session.commit()
    log_activity('shelter', f'Shelter "{shelter.shelter_name}" rejected by {current_user.username}.', user_id=current_user.id)
    flash(f'Shelter "{shelter.shelter_name}" has been rejected.', 'danger')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/procurement')
@login_required
@role_required('super_admin')
def procurement_requests():
    from app.models.procurement import ProcurementRequest
    from app.models.warehouse import Warehouse
    from app.services.geo_services import find_matching_warehouses

    requests = ProcurementRequest.query.order_by(
        ProcurementRequest.created_at.desc()
    ).all()

    # Pre-calculate GIS matches for each pending request (same as gov officer view)
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
    log_activity('procurement', f'Procurement request #{proc.id} ({proc.requested_sku}) approved by {current_user.username}.', user_id=current_user.id)
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
    log_activity('procurement', f'Procurement request #{proc.id} ({proc.requested_sku}) rejected by {current_user.username}.', user_id=current_user.id)
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
    log_activity('warehouse', f'Warehouse "{warehouse_name}" created by {current_user.username}.', user_id=current_user.id)
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
    log_activity('warehouse', f'Warehouse "{warehouse.warehouse_name}" approved by {current_user.username}.', user_id=current_user.id)
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
    log_activity('warehouse', f'Warehouse "{warehouse.warehouse_name}" rejected by {current_user.username}.', user_id=current_user.id)
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


@admin_bp.route('/users')
@login_required
@role_required('super_admin')
def users():
    role_filter = request.args.get('role', '')
    status_filter = request.args.get('status', '')

    query = User.query.filter(User.role_level != 'citizen')

    if role_filter:
        query = query.filter_by(role_level=role_filter)
    if status_filter:
        query = query.filter_by(status=status_filter)

    all_users = query.order_by(User.created_at.desc()).all()

    return render_template('super_admin/users.html',
                           users=all_users,
                           role_filter=role_filter,
                           status_filter=status_filter)


@admin_bp.route('/users/toggle/<int:user_id>')
@login_required
@role_required('super_admin')
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("You can't change your own account status.", 'danger')
        return redirect(url_for('admin.users'))

    if user.status == 'active':
        user.status = 'rejected'
        db.session.commit()
        log_activity('user', f'{user.username} ({user.role_level}) deactivated by {current_user.username}.', user_id=current_user.id)
        flash(f'{user.username} has been deactivated.', 'danger')
    else:
        user.status = 'active'
        db.session.commit()
        log_activity('user', f'{user.username} ({user.role_level}) reactivated by {current_user.username}.', user_id=current_user.id)
        flash(f'{user.username} has been reactivated.', 'success')

    return redirect(url_for('admin.users'))


@admin_bp.route('/analytics')
@login_required
@role_required('super_admin')
def analytics():
    from datetime import datetime, timedelta
    from app.models.warehouse import Warehouse
    from app.models.shelter import Shelter
    from app.models.alert import Alert
    from app.models.procurement import ProcurementRequest
    from app.services.activity_service import get_recent_activity

    # --- Users ---
    all_users = User.query.filter(User.role_level != 'citizen').all()
    by_role = {}
    for u in all_users:
        by_role[u.role_level] = by_role.get(u.role_level, 0) + 1
    user_stats = {'total': len(all_users), 'by_role': by_role}

    # --- Shelters ---
    active_shelters = Shelter.query.filter_by(status='active').all()
    shelter_stats = {'total': len(active_shelters), 'list': active_shelters}

    # --- Warehouses ---
    active_warehouses = Warehouse.query.filter_by(status='active').all()
    warehouse_stats = {'total': len(active_warehouses), 'list': active_warehouses}

    # --- Alerts ---
    alert_stats = {
        'unread': Alert.query.filter_by(is_read=False).count(),
        'total': Alert.query.count(),
    }

    # --- Procurement status breakdown ---
    all_requests = ProcurementRequest.query.all()
    procurement_stats = {
        'total': len(all_requests),
        'pending': sum(1 for r in all_requests if r.status_state == 'pending'),
        'approved': sum(1 for r in all_requests if r.status_state == 'approved'),
        'dispatched': sum(1 for r in all_requests if r.status_state == 'dispatched'),
        'fulfilled': sum(1 for r in all_requests if r.status_state == 'fulfilled'),
        'rejected': sum(1 for r in all_requests if r.status_state == 'rejected'),
    }

    # --- Procurement requests over the last 7 days ---
    today = datetime.utcnow().date()
    procurement_chart = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = sum(1 for r in all_requests if r.created_at and r.created_at.date() == day)
        procurement_chart.append({'date': day.strftime('%m/%d'), 'count': count})

    # --- GIS map data ---
    shelters_geo = []
    for s in active_shelters:
        if s.latitude is not None and s.longitude is not None:
            capacity = s.maximum_capacity or 0
            occupancy = s.current_occupancy_count or 0
            occupancy_pct = round((occupancy / capacity) * 100) if capacity else 0
            shelters_geo.append({
                'name': s.shelter_name,
                'lat': s.latitude,
                'lng': s.longitude,
                'occupancy': occupancy,
                'capacity': capacity,
                'occupancy_pct': occupancy_pct,
            })

    warehouses_geo = []
    for w in active_warehouses:
        if w.latitude is not None and w.longitude is not None:
            stock_items = [{
                'name': item.sku_name,
                'qty': item.quantity_available,
                'unit': item.metric_unit,
                'low': item.is_low,
            } for item in w.inventory]
            warehouses_geo.append({
                'name': w.warehouse_name,
                'lat': w.latitude,
                'lng': w.longitude,
                'low_stock_count': sum(1 for i in w.inventory if i.is_low),
                'stock_items': stock_items,
            })

    geo_data = {'shelters': shelters_geo, 'warehouses': warehouses_geo}
    recent_activity = get_recent_activity(25)

    return render_template('super_admin/analytics.html',
                           user_stats=user_stats,
                           shelter_stats=shelter_stats,
                           warehouse_stats=warehouse_stats,
                           alert_stats=alert_stats,
                           procurement_stats=procurement_stats,
                           procurement_chart=procurement_chart,
                           geo_data=geo_data,
                           recent_activity=recent_activity)