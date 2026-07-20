from flask_login import login_required, current_user
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.extensions import db
from app.models.user import User
from app.models.shelter import Shelter
from app.utils import role_required
from app.services.activity_service import log_activity
from app.services.notification_service import notify_user, notify_role, notify_segment, build_segment_query

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
    notify_user(user, f'Your {user.role_level.replace("_", " ").title()} account has been approved. You can now log in.',
                title='Account approved', urgency='info')
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
    notify_user(user, 'Your account application has been rejected. Contact an administrator for details.',
                title='Account rejected', urgency='warning')
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
    notify_user(shelter.created_by, f'Your shelter "{shelter.shelter_name}" has been approved and is now active.',
                title='Shelter approved', urgency='info')
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
    notify_user(shelter.created_by, f'Your shelter "{shelter.shelter_name}" was not approved.',
                title='Shelter rejected', urgency='warning')
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
    notify_user(proc.requested_by,
                f'Your request for {proc.quantity_needed} {proc.metric_unit} of {proc.requested_sku} has been approved.',
                title='Procurement approved', urgency='info')
    for a in proc.fulfilled_warehouse.assignments:
        notify_user(a.user,
                    f'New dispatch task: {proc.quantity_needed} {proc.metric_unit} of {proc.requested_sku} '
                    f'for {proc.shelter.shelter_name}.',
                    title='New dispatch task', urgency='warning')
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
    notify_user(proc.requested_by,
                f'Your request for {proc.quantity_needed} {proc.metric_unit} of {proc.requested_sku} was rejected.',
                title='Procurement rejected', urgency='warning')
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
    notify_user(warehouse.created_by, f'Your warehouse "{warehouse.warehouse_name}" has been approved and is now active.',
                title='Warehouse approved', urgency='info')
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
    notify_user(warehouse.created_by, f'Your warehouse "{warehouse.warehouse_name}" was not approved.',
                title='Warehouse rejected', urgency='warning')
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
        notify_user(user, 'Your account has been deactivated. Contact an administrator for details.',
                    title='Account deactivated', urgency='warning')
        flash(f'{user.username} has been deactivated.', 'danger')
    else:
        user.status = 'active'
        db.session.commit()
        log_activity('user', f'{user.username} ({user.role_level}) reactivated by {current_user.username}.', user_id=current_user.id)
        notify_user(user, 'Your account has been reactivated. You can log in again.',
                    title='Account reactivated', urgency='info')
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

    # --- Citizen location points (previously no citizen layer existed at all) ---
    citizens_geo = []
    citizen_users = User.query.filter(
        User.role_level == 'citizen',
        User.latitude.isnot(None),
        User.longitude.isnot(None),
    ).all()
    for u in citizen_users:
        citizens_geo.append({
            'name': u.full_name or u.username,
            'lat': u.latitude,
            'lng': u.longitude,
        })

    geo_data = {'shelters': shelters_geo, 'warehouses': warehouses_geo, 'citizens': citizens_geo}
    recent_activity = get_recent_activity(25)

    # --- Recent check-in campaigns (response-rate summary) ---
    from app.models.checkin import CheckIn
    recent_checkins = CheckIn.query.order_by(CheckIn.created_at.desc()).limit(5).all()

    return render_template('super_admin/analytics.html',
                           user_stats=user_stats,
                           shelter_stats=shelter_stats,
                           warehouse_stats=warehouse_stats,
                           alert_stats=alert_stats,
                           procurement_stats=procurement_stats,
                           procurement_chart=procurement_chart,
                           geo_data=geo_data,
                           recent_activity=recent_activity,
                           recent_checkins=recent_checkins)


@admin_bp.route('/announcements', methods=['GET', 'POST'])
@login_required
@role_required('super_admin')
def announcements():
    from app.models.shelter import Shelter
    from app.models.notification import Notification

    shelters = Shelter.query.filter_by(status='active').order_by(Shelter.shelter_name).all()

    # Distinct existing location values, just to power <datalist> suggestions —
    # doesn't restrict input, so this still works for any country in the world.
    countries = sorted({u.country for u in User.query.filter(User.country.isnot(None)).all()})
    regions = sorted({u.region for u in User.query.filter(User.region.isnot(None)).all()})
    cities = sorted({u.city for u in User.query.filter(User.city.isnot(None)).all()})

    preview_count = None
    form_values = {}

    if request.method == 'POST':
        roles = request.form.getlist('roles')
        country = request.form.get('country', '').strip() or None
        region = request.form.get('region', '').strip() or None
        city = request.form.get('city', '').strip() or None
        shelter_id = request.form.get('shelter_id', '').strip()
        shelter_id = int(shelter_id) if shelter_id else None
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()
        urgency = request.form.get('urgency', 'info')

        form_values = {
            'roles': roles, 'country': country, 'region': region, 'city': city,
            'shelter_id': shelter_id, 'title': title, 'message': message, 'urgency': urgency,
        }

        if 'preview' in request.form:
            preview_count = build_segment_query(
                roles=roles or None, country=country, region=region, city=city, shelter_id=shelter_id
            ).count()
        elif 'send' in request.form:
            if not message:
                flash('Message text is required.', 'danger')
            else:
                notification = notify_segment(
                    message, title=title or None, urgency=urgency,
                    roles=roles or None, country=country, region=region, city=city,
                    shelter_id=shelter_id, sent_by_id=current_user.id
                )
                log_activity('user', f'{current_user.username} sent an announcement to '
                                      f'{len(notification.deliveries)} recipient(s): "{title or message[:40]}".',
                            user_id=current_user.id)
                flash(f'Announcement sent — {notification.delivered_count} delivered, '
                      f'{notification.failed_count} failed, {notification.skipped_count} skipped '
                      f'(not connected to Telegram or opted out).', 'success')
                return redirect(url_for('admin.announcements'))

    history = Notification.query.filter_by(category='announcement').order_by(
        Notification.created_at.desc()
    ).limit(20).all()

    return render_template('super_admin/announcements.html',
                           shelters=shelters, countries=countries, regions=regions, cities=cities,
                           preview_count=preview_count, form_values=form_values, history=history)


@admin_bp.route('/checkins', methods=['GET', 'POST'])
@login_required
@role_required('super_admin')
def checkins():
    """
    "Are you safe?" / roll-call campaigns. Same targeting shape as
    Announcements, but tracks per-recipient responses (via checkin_service)
    instead of just delivery — so this screen can show "X of Y responded,
    Z need help" rather than just "sent to N people".
    """
    from app.models.checkin import CheckIn
    from app.services import checkin_service

    shelters = Shelter.query.filter_by(status='active').order_by(Shelter.shelter_name).all()
    countries = sorted({u.country for u in User.query.filter(User.country.isnot(None)).all()})
    regions = sorted({u.region for u in User.query.filter(User.region.isnot(None)).all()})
    cities = sorted({u.city for u in User.query.filter(User.city.isnot(None)).all()})

    preview_count = None
    form_values = {}

    if request.method == 'POST':
        roles = request.form.getlist('roles')
        country = request.form.get('country', '').strip() or None
        region = request.form.get('region', '').strip() or None
        city = request.form.get('city', '').strip() or None
        shelter_id = request.form.get('shelter_id', '').strip()
        shelter_id = int(shelter_id) if shelter_id else None
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()

        form_values = {
            'roles': roles, 'country': country, 'region': region, 'city': city,
            'shelter_id': shelter_id, 'title': title, 'message': message,
        }

        if 'preview' in request.form:
            preview_count = build_segment_query(
                roles=roles or None, country=country, region=region, city=city, shelter_id=shelter_id
            ).count()
        elif 'send' in request.form:
            if not message or not title:
                flash('Title and message are both required.', 'danger')
            else:
                checkin = checkin_service.launch_checkin(
                    title, message, roles=roles or None, country=country, region=region,
                    city=city, shelter_id=shelter_id, sent_by_id=current_user.id,
                )
                log_activity('user', f'{current_user.username} launched check-in "{title}" to '
                                      f'{checkin.target_count} recipient(s).', user_id=current_user.id)
                flash(f'Check-in sent to {checkin.target_count} people. Responses will appear below as they come in.', 'success')
                return redirect(url_for('admin.checkins'))

    history = CheckIn.query.order_by(CheckIn.created_at.desc()).limit(20).all()

    return render_template('super_admin/checkins.html',
                           shelters=shelters, countries=countries, regions=regions, cities=cities,
                           preview_count=preview_count, form_values=form_values, history=history)


@admin_bp.route('/checkins/<int:checkin_id>')
@login_required
@role_required('super_admin')
def checkin_detail(checkin_id):
    from app.models.checkin import CheckIn
    from app.services.geo_service import get_all_locations_geojson
    checkin = CheckIn.query.get_or_404(checkin_id)
    geo_data = get_all_locations_geojson(checkin_id=checkin_id)
    no_response = [r for r in checkin.responses if r.status == 'pending']
    return render_template('super_admin/checkin_detail.html', checkin=checkin,
                           geo_data=geo_data, no_response=no_response)


# ─── Citizen verification / beneficiary directory ───────────────────────────
# Previously there was no screen anywhere — for either Gov Officer or Super
# Admin — to browse or search citizen verification records at all. The only
# way a Beneficiary record became visible to staff was as a side effect of
# approving a specific ShelterRegistrationRequest.

@admin_bp.route('/beneficiaries')
@login_required
@role_required('super_admin')
def beneficiaries():
    from app.services.beneficiary_service import search_and_filter
    q = request.args.get('q', '').strip()
    verified = request.args.get('verified', '')  # '', 'yes', 'no'
    results = search_and_filter(q=q, verified=verified)
    return render_template('super_admin/beneficiaries.html', results=results, q=q, verified=verified)



 # ─── Super Admin Override Routes ─────────────────────────────────────────────
# These allow Super Admin to access pages normally restricted to other roles

@admin_bp.route('/warehouse/transfers')
@login_required
@role_required('super_admin')
def warehouse_transfers():
    from app.models.stock_transfer import StockTransfer
    from app.models.warehouse import Warehouse
    warehouses = Warehouse.query.filter_by(status='active').all()
    all_transfers = StockTransfer.query.order_by(
        StockTransfer.created_at.desc()
    ).all()
    return render_template('warehouse_manager/transfers.html',
                           outgoing=all_transfers,
                           incoming=all_transfers,
                           my_warehouses=warehouses,
                           all_warehouses=warehouses,
                           is_admin_view=True)


@admin_bp.route('/warehouse/catalog')
@login_required
@role_required('super_admin')
def warehouse_catalog():
    from app.models.product import Product
    products = Product.query.order_by(
        Product.category, Product.name
    ).all()
    return render_template('warehouse_manager/catalog.html',
                           products=products)


@admin_bp.route('/warehouse/catalog/add', methods=['POST'])
@login_required
@role_required('super_admin')
def add_product():
    from app.models.product import Product
    name = request.form.get('name')
    category = request.form.get('category')
    unit = request.form.get('default_unit')
    description = request.form.get('description')
    if not Product.query.filter_by(name=name).first():
        product = Product(
            name=name, category=category,
            default_unit=unit, description=description,
            is_active=True, created_by_id=current_user.id
        )
        db.session.add(product)
        db.session.commit()
        flash(f'{name} added to catalog.', 'success')
    else:
        flash('Product already exists.', 'warning')
    return redirect(url_for('admin.warehouse_catalog'))


@admin_bp.route('/gov-view/procurement')
@login_required
@role_required('super_admin')
def gov_procurement_view():
    from app.models.procurement import ProcurementRequest
    from app.models.warehouse import Warehouse
    from app.services.geo_services import find_matching_warehouses
    requests = ProcurementRequest.query.order_by(
        ProcurementRequest.created_at.desc()
    ).all()
    gis_matches = {}
    for req in requests:
        if req.status_state == 'pending' and req.shelter:
            matches = find_matching_warehouses(
                req.shelter, req.requested_sku, req.quantity_needed
            )
            gis_matches[req.id] = matches
    warehouses = Warehouse.query.filter_by(status='active').all()
    return render_template('gov_officer/procurement.html',
                           requests=requests,
                           warehouses=warehouses,
                           gis_matches=gis_matches)


@admin_bp.route('/gov-view/warehouses')
@login_required
@role_required('super_admin')
def gov_warehouses_view():
    from app.models.warehouse import Warehouse
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
                           all_warehouses=active_warehouses,
                           base_url='admin')


@admin_bp.route('/gov-view/warehouse-managers')
@login_required
@role_required('super_admin')
def gov_warehouse_managers_view():
    from app.models.warehouse import Warehouse
    from app.models.user import User
    pending_wm = User.query.filter_by(
        role_level='warehouse_manager', status='pending'
    ).all()
    active_wm = User.query.filter_by(
        role_level='warehouse_manager', status='active'
    ).all()
    warehouses = Warehouse.query.filter_by(status='active').all()
    return render_template('gov_officer/warehouse_managers.html',
                           pending_wm=pending_wm,
                           active_wm=active_wm,
                           warehouses=warehouses)   