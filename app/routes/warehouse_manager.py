from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.warehouse import Warehouse, InventoryStock
from app.models.warehouse_assignment import WarehouseAssignment
from app.models.procurement import ProcurementRequest
from app.models.product import Product
from app.models.stock_transfer import StockTransfer
from app.models.alert import Alert
from app.services.alert_service import check_warehouse_stock_alerts
from app.utils import role_required, active_required
from app.services.activity_service import log_activity
from app.services.notification_service import notify_user
from datetime import datetime

warehouse_bp = Blueprint('warehouse', __name__)


# ─── Helpers ────────────────────────────────────────────────────────────────

def get_my_warehouses():
    assignments = WarehouseAssignment.query.filter_by(
        user_id=current_user.id
    ).all()
    return [a.warehouse for a in assignments if a.warehouse.status == 'active']


def get_my_warehouse_ids():
    return [w.id for w in get_my_warehouses()]


# ─── Dashboard ──────────────────────────────────────────────────────────────

@warehouse_bp.route('/dashboard')
@login_required
@role_required('warehouse_manager')
@active_required
def dashboard():
    my_warehouses = get_my_warehouses()
    warehouse_ids = [w.id for w in my_warehouses]

    pending_dispatches = ProcurementRequest.query.filter(
        ProcurementRequest.fulfilled_warehouse_id.in_(warehouse_ids),
        ProcurementRequest.status_state == 'approved'
    ).all() if warehouse_ids else []

    incoming_transfers = StockTransfer.query.filter(
        StockTransfer.to_warehouse_id.in_(warehouse_ids),
        StockTransfer.status == 'dispatched'
    ).all() if warehouse_ids else []

    low_stock_items = []
    for w in my_warehouses:
        low_stock_items += [i for i in w.inventory if i.is_low]

    pending_my_warehouse = Warehouse.query.filter_by(
        created_by_id=current_user.id,
        status='pending_approval'
    ).all()

    return render_template('warehouse_manager/dashboard.html',
                           my_warehouses=my_warehouses,
                           pending_dispatches=pending_dispatches,
                           incoming_transfers=incoming_transfers,
                           low_stock_items=low_stock_items,
                           pending_my_warehouse=pending_my_warehouse)


# ─── Warehouse CRUD ─────────────────────────────────────────────────────────

@warehouse_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('warehouse_manager')
@active_required
def create_warehouse():
    if request.method == 'POST':
        warehouse_name = request.form.get('warehouse_name')
        address = request.form.get('address')
        lat = request.form.get('latitude')
        lng = request.form.get('longitude')

        warehouse = Warehouse(
            warehouse_name=warehouse_name,
            address=address,
            latitude=float(lat) if lat else None,
            longitude=float(lng) if lng else None,
            status='pending_approval',
            created_by_id=current_user.id
        )
        db.session.add(warehouse)
        db.session.commit()

        log_activity('warehouse', f'Warehouse "{warehouse_name}" submitted for approval by {current_user.username}.', user_id=current_user.id)
        from app.services.notification_service import notify_role
        from app.services.telegram_api import build_inline_keyboard
        notify_role('gov_officer', f'New warehouse "{warehouse_name}" submitted by {current_user.username}, awaiting approval.',
                    title='New warehouse submitted', urgency='info',
                    reply_markup=build_inline_keyboard([[
                        ('✅ Approve', f'apr_wh:{warehouse.id}'),
                        ('❌ Reject', f'rej_wh:{warehouse.id}'),
                    ]]))
        flash('Warehouse submitted for approval.', 'success')
        return redirect(url_for('warehouse.dashboard'))

    return render_template('warehouse_manager/create_warehouse.html')


# ─── Stock Management ────────────────────────────────────────────────────────

@warehouse_bp.route('/stock/<int:warehouse_id>')
@login_required
@role_required('warehouse_manager')
@active_required
def manage_stock(warehouse_id):
    if warehouse_id not in get_my_warehouse_ids():
        flash('Access denied — not your warehouse.', 'danger')
        return redirect(url_for('warehouse.dashboard'))

    warehouse = Warehouse.query.get_or_404(warehouse_id)
    products = Product.query.filter_by(is_active=True).order_by(
        Product.category, Product.name
    ).all()
    return render_template('warehouse_manager/stock.html',
                           warehouse=warehouse,
                           products=products)


@warehouse_bp.route('/stock/<int:warehouse_id>/add', methods=['POST'])
@login_required
@role_required('warehouse_manager')
@active_required
def add_stock(warehouse_id):
    if warehouse_id not in get_my_warehouse_ids():
        flash('Access denied.', 'danger')
        return redirect(url_for('warehouse.dashboard'))

    product_id = int(request.form.get('product_id'))
    quantity = int(request.form.get('quantity'))
    product = Product.query.get_or_404(product_id)

    existing = InventoryStock.query.filter_by(
        warehouse_id=warehouse_id,
        sku_name=product.name
    ).first()

    if existing:
        existing.quantity_available += quantity
        check_warehouse_stock_alerts(existing)
    else:
        new_item = InventoryStock(
            warehouse_id=warehouse_id,
            sku_name=product.name,
            quantity_available=quantity,
            metric_unit=product.default_unit,
            threshold=20
        )
        db.session.add(new_item)

    db.session.commit()
    flash(f'{product.name} stock updated.', 'success')
    return redirect(url_for('warehouse.manage_stock', warehouse_id=warehouse_id))


@warehouse_bp.route('/stock/<int:warehouse_id>/update/<int:item_id>', methods=['POST'])
@login_required
@role_required('warehouse_manager')
@active_required
def update_stock(warehouse_id, item_id):
    if warehouse_id not in get_my_warehouse_ids():
        flash('Access denied.', 'danger')
        return redirect(url_for('warehouse.dashboard'))

    item = InventoryStock.query.get_or_404(item_id)
    new_qty = int(request.form.get('quantity'))
    new_threshold = int(request.form.get('threshold', item.threshold))
    item.quantity_available = new_qty
    item.threshold = new_threshold
    check_warehouse_stock_alerts(item)
    db.session.commit()
    flash(f'{item.sku_name} updated.', 'success')
    return redirect(url_for('warehouse.manage_stock', warehouse_id=warehouse_id))


@warehouse_bp.route('/stock/<int:warehouse_id>/remove/<int:item_id>')
@login_required
@role_required('warehouse_manager')
@active_required
def remove_stock(warehouse_id, item_id):
    if warehouse_id not in get_my_warehouse_ids():
        flash('Access denied.', 'danger')
        return redirect(url_for('warehouse.dashboard'))

    item = InventoryStock.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash(f'{item.sku_name} removed from inventory.', 'info')
    return redirect(url_for('warehouse.manage_stock', warehouse_id=warehouse_id))


# ─── Dispatch Procurement ────────────────────────────────────────────────────

@warehouse_bp.route('/dispatch/<int:request_id>', methods=['POST'])
@login_required
@role_required('warehouse_manager')
@active_required
def dispatch_request(request_id):
    proc = ProcurementRequest.query.get_or_404(request_id)

    if proc.fulfilled_warehouse_id not in get_my_warehouse_ids():
        flash('This request is not assigned to your warehouse.', 'danger')
        return redirect(url_for('warehouse.dashboard'))

    if proc.status_state != 'approved':
        flash('Only approved requests can be dispatched.', 'warning')
        return redirect(url_for('warehouse.dashboard'))

    # Deduct from warehouse stock
    stock_item = InventoryStock.query.filter_by(
        warehouse_id=proc.fulfilled_warehouse_id,
        sku_name=proc.requested_sku
    ).first()

    if stock_item:
        if stock_item.quantity_available < proc.quantity_needed:
            flash(f'Insufficient stock. Available: {stock_item.quantity_available} {stock_item.metric_unit}.', 'danger')
            return redirect(url_for('warehouse.dashboard'))
        stock_item.quantity_available -= proc.quantity_needed
        check_warehouse_stock_alerts(stock_item)
    else:
        flash(f'Stock item "{proc.requested_sku}" not found in warehouse.', 'danger')
        return redirect(url_for('warehouse.dashboard'))

    proc.status_state = 'dispatched'
    db.session.commit()
    log_activity('procurement', f'{current_user.username} dispatched {proc.quantity_needed} {proc.metric_unit} of {proc.requested_sku} to {proc.shelter.shelter_name}.', user_id=current_user.id)
    notify_user(proc.requested_by,
                f'Your request for {proc.quantity_needed} {proc.metric_unit} of {proc.requested_sku} has been dispatched and is on the way.',
                title='Goods dispatched', urgency='info')
    flash(f'Dispatched {proc.quantity_needed} {proc.metric_unit} of {proc.requested_sku} to {proc.shelter.shelter_name}.', 'success')
    return redirect(url_for('warehouse.dashboard'))


# ─── Stock Transfers ─────────────────────────────────────────────────────────

@warehouse_bp.route('/transfers')
@login_required
@role_required('warehouse_manager')
@active_required
def transfers():
    my_ids = get_my_warehouse_ids()

    outgoing = StockTransfer.query.filter(
        StockTransfer.from_warehouse_id.in_(my_ids)
    ).order_by(StockTransfer.created_at.desc()).all()

    incoming = StockTransfer.query.filter(
        StockTransfer.to_warehouse_id.in_(my_ids)
    ).order_by(StockTransfer.created_at.desc()).all()

    all_warehouses = Warehouse.query.filter_by(status='active').all()
    my_warehouses = get_my_warehouses()

    return render_template('warehouse_manager/transfers.html',
                           outgoing=outgoing,
                           incoming=incoming,
                           my_warehouses=my_warehouses,
                           all_warehouses=all_warehouses)


@warehouse_bp.route('/transfers/initiate', methods=['POST'])
@login_required
@role_required('warehouse_manager')
@active_required
def initiate_transfer():
    from_warehouse_id = int(request.form.get('from_warehouse_id'))
    to_warehouse_id = int(request.form.get('to_warehouse_id'))
    sku_name = request.form.get('sku_name')
    quantity = int(request.form.get('quantity'))
    notes = request.form.get('notes')

    if from_warehouse_id not in get_my_warehouse_ids():
        flash('You can only transfer from your own warehouses.', 'danger')
        return redirect(url_for('warehouse.transfers'))

    if from_warehouse_id == to_warehouse_id:
        flash('Cannot transfer to the same warehouse.', 'warning')
        return redirect(url_for('warehouse.transfers'))

    # Verify and deduct stock
    stock_item = InventoryStock.query.filter_by(
        warehouse_id=from_warehouse_id,
        sku_name=sku_name
    ).first()

    if not stock_item:
        flash(f'Item "{sku_name}" not found in your warehouse.', 'danger')
        return redirect(url_for('warehouse.transfers'))

    if stock_item.quantity_available < quantity:
        flash(f'Insufficient stock. Available: {stock_item.quantity_available} {stock_item.metric_unit}.', 'danger')
        return redirect(url_for('warehouse.transfers'))

    # Deduct from source
    stock_item.quantity_available -= quantity
    check_warehouse_stock_alerts(stock_item)

    transfer = StockTransfer(
        from_warehouse_id=from_warehouse_id,
        to_warehouse_id=to_warehouse_id,
        sku_name=sku_name,
        metric_unit=stock_item.metric_unit,
        quantity=quantity,
        notes=notes,
        status='dispatched',
        initiated_by_id=current_user.id
    )
    db.session.add(transfer)
    db.session.commit()

    to_warehouse = Warehouse.query.get(to_warehouse_id)
    if to_warehouse:
        for a in to_warehouse.assignments:
            notify_user(a.user, f'Incoming transfer: {quantity} {stock_item.metric_unit} of {sku_name} '
                                 f'from {current_user.username}\'s warehouse.',
                        title='Incoming stock transfer', urgency='info')

    flash(f'Transfer of {quantity} {stock_item.metric_unit} of {sku_name} initiated.', 'success')
    return redirect(url_for('warehouse.transfers'))


@warehouse_bp.route('/transfers/confirm/<int:transfer_id>', methods=['POST'])
@login_required
@role_required('warehouse_manager')
@active_required
def confirm_transfer(transfer_id):
    transfer = StockTransfer.query.get_or_404(transfer_id)

    if transfer.to_warehouse_id not in get_my_warehouse_ids():
        flash('This transfer is not destined for your warehouse.', 'danger')
        return redirect(url_for('warehouse.transfers'))

    if transfer.status != 'dispatched':
        flash('Only dispatched transfers can be confirmed.', 'warning')
        return redirect(url_for('warehouse.transfers'))

    # Add stock to receiving warehouse
    existing = InventoryStock.query.filter_by(
        warehouse_id=transfer.to_warehouse_id,
        sku_name=transfer.sku_name
    ).first()

    if existing:
        existing.quantity_available += transfer.quantity
    else:
        new_item = InventoryStock(
            warehouse_id=transfer.to_warehouse_id,
            sku_name=transfer.sku_name,
            quantity_available=transfer.quantity,
            metric_unit=transfer.metric_unit,
            threshold=20
        )
        db.session.add(new_item)

    transfer.status = 'confirmed'
    transfer.confirmed_by_id = current_user.id
    transfer.confirmed_at = datetime.utcnow()
    db.session.commit()

    log_activity('warehouse', f'{current_user.username} confirmed transfer of {transfer.quantity} {transfer.metric_unit} of {transfer.sku_name}.', user_id=current_user.id)
    if transfer.initiated_by:
        notify_user(transfer.initiated_by, f'Your transfer of {transfer.quantity} {transfer.metric_unit} of '
                                            f'{transfer.sku_name} was received and confirmed by {current_user.username}.',
                    title='Transfer confirmed', urgency='info')
    flash(f'Transfer confirmed. {transfer.quantity} {transfer.metric_unit} of {transfer.sku_name} added to your warehouse.', 'success')
    return redirect(url_for('warehouse.transfers'))


# ─── Product Catalog ─────────────────────────────────────────────────────────

@warehouse_bp.route('/catalog')
@login_required
@role_required('warehouse_manager', 'gov_officer', 'super_admin')
@active_required
def catalog():
    products = Product.query.order_by(Product.category, Product.name).all()
    return render_template('warehouse_manager/catalog.html', products=products)


@warehouse_bp.route('/catalog/add', methods=['POST'])
@login_required
@role_required('warehouse_manager', 'gov_officer', 'super_admin')
@active_required
def add_product():
    name = request.form.get('name')
    category = request.form.get('category')
    unit = request.form.get('default_unit')
    description = request.form.get('description')

    if Product.query.filter_by(name=name).first():
        flash('Product already exists in catalog.', 'warning')
        return redirect(url_for('warehouse.catalog'))

    product = Product(
        name=name,
        category=category,
        default_unit=unit,
        description=description,
        is_active=True,
        created_by_id=current_user.id
    )
    db.session.add(product)
    db.session.commit()
    flash(f'{name} added to catalog.', 'success')
    return redirect(url_for('warehouse.catalog'))


@warehouse_bp.route('/catalog/toggle/<int:product_id>')
@login_required
@role_required('warehouse_manager', 'gov_officer', 'super_admin')
@active_required
def toggle_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.is_active = not product.is_active
    db.session.commit()
    flash(f'{product.name} {"activated" if product.is_active else "deactivated"}.', 'info')
    return redirect(url_for('warehouse.catalog'))