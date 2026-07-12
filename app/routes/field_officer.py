from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.shelter import Shelter, ShelterInventory
from app.models.procurement import ProcurementRequest
from app.models.beneficiary import Beneficiary
from app.models.shelter_registration import ShelterRegistrationRequest
from app.services.alert_service import check_shelter_inventory_alerts, create_alert
from app.utils import role_required, active_required

field_bp = Blueprint('field', __name__)


@field_bp.route('/dashboard')
@login_required
@role_required('field_officer')
@active_required
def dashboard():
    my_shelters = Shelter.query.filter(
        Shelter.created_by_id == current_user.id,
        Shelter.status == 'active'
    ).all()

    pending_shelters = Shelter.query.filter_by(
        created_by_id=current_user.id,
        status='pending_approval'
    ).all()

    all_requests = []
    low_stock_items = []

    for shelter in my_shelters:
        all_requests += ProcurementRequest.query.filter_by(
            origin_shelter_id=shelter.id
        ).order_by(ProcurementRequest.created_at.desc()).limit(5).all()
        low_stock_items += [item for item in shelter.inventory_items if item.is_low]

    shelter_count = Shelter.query.filter(
        Shelter.created_by_id == current_user.id,
        Shelter.status.in_(['active', 'pending_approval'])
    ).count()

    return render_template('field_officer/dashboard.html',
                           my_shelters=my_shelters,
                           pending_shelters=pending_shelters,
                           my_requests=all_requests,
                           low_stock_items=low_stock_items,
                           shelter_count=shelter_count)


@field_bp.route('/shelter/create', methods=['GET', 'POST'])
@login_required
@role_required('field_officer')
@active_required
def create_shelter():
    existing_count = Shelter.query.filter(
        Shelter.created_by_id == current_user.id,
        Shelter.status.in_(['active', 'pending_approval'])
    ).count()

    if existing_count >= 10:
        flash('You have reached the maximum limit of 10 shelters.', 'warning')
        return redirect(url_for('field.dashboard'))

    if request.method == 'POST':
        shelter_name = request.form.get('shelter_name')
        address = request.form.get('address')
        max_capacity = request.form.get('maximum_capacity')
        lat = request.form.get('latitude')
        lng = request.form.get('longitude')

        new_shelter = Shelter(
            shelter_name=shelter_name,
            address=address,
            maximum_capacity=int(max_capacity),
            latitude=float(lat) if lat else None,
            longitude=float(lng) if lng else None,
            status='pending_approval',
            created_by_id=current_user.id
        )
        db.session.add(new_shelter)
        db.session.commit()

        create_alert(
            alert_type='new_procurement_request',
            message=f'New shelter "{shelter_name}" submitted by {current_user.username} — awaiting approval.',
            shelter_id=new_shelter.id
        )

        flash('Shelter submitted for approval.', 'success')
        return redirect(url_for('field.dashboard'))

    return render_template('field_officer/create_shelter.html')


@field_bp.route('/shelter/<int:shelter_id>/inventory')
@login_required
@role_required('field_officer')
@active_required
def shelter_inventory(shelter_id):
    shelter = Shelter.query.filter_by(
        id=shelter_id,
        created_by_id=current_user.id,
        status='active'
    ).first_or_404()
    return render_template('field_officer/inventory.html', shelter=shelter)


@field_bp.route('/shelter/<int:shelter_id>/inventory/add', methods=['POST'])
@login_required
@role_required('field_officer')
@active_required
def add_inventory_item(shelter_id):
    shelter = Shelter.query.filter_by(
        id=shelter_id,
        created_by_id=current_user.id,
        status='active'
    ).first_or_404()

    item_name = request.form.get('item_name')
    quantity = int(request.form.get('quantity'))
    threshold = int(request.form.get('threshold'))
    metric_unit = request.form.get('metric_unit')

    existing_item = ShelterInventory.query.filter_by(
        shelter_id=shelter.id,
        item_name=item_name
    ).first()

    if existing_item:
        existing_item.quantity = quantity
        existing_item.threshold = threshold
        check_shelter_inventory_alerts(existing_item)
    else:
        new_item = ShelterInventory(
            shelter_id=shelter.id,
            item_name=item_name,
            quantity=quantity,
            threshold=threshold,
            metric_unit=metric_unit
        )
        db.session.add(new_item)
        db.session.flush()
        check_shelter_inventory_alerts(new_item)

    db.session.commit()
    flash(f'{item_name} updated in inventory.', 'success')
    return redirect(url_for('field.shelter_inventory', shelter_id=shelter.id))


@field_bp.route('/shelter/inventory/update/<int:item_id>', methods=['POST'])
@login_required
@role_required('field_officer')
@active_required
def update_inventory_item(item_id):
    item = ShelterInventory.query.get_or_404(item_id)
    item.quantity = int(request.form.get('quantity'))
    check_shelter_inventory_alerts(item)
    db.session.commit()
    flash(f'{item.item_name} quantity updated.', 'success')
    return redirect(url_for('field.shelter_inventory', shelter_id=item.shelter_id))


@field_bp.route('/procurement/create', methods=['GET', 'POST'])
@login_required
@role_required('field_officer')
@active_required
def create_procurement():
    from app.models.product import Product
    my_shelters = Shelter.query.filter_by(
        created_by_id=current_user.id,
        status='active'
    ).all()

    if not my_shelters:
        flash('You need an active shelter to raise procurement requests.', 'warning')
        return redirect(url_for('field.dashboard'))

    products = Product.query.filter_by(is_active=True).order_by(
        Product.category, Product.name
    ).all()

    if request.method == 'POST':
        shelter_id = int(request.form.get('shelter_id'))
        product_id = int(request.form.get('product_id'))
        quantity_needed = int(request.form.get('quantity_needed'))
        notes = request.form.get('notes')

        product = Product.query.get_or_404(product_id)
        shelter = Shelter.query.get_or_404(shelter_id)

        new_request = ProcurementRequest(
            origin_shelter_id=shelter_id,
            requested_by_id=current_user.id,
            requested_sku=product.name,
            quantity_needed=quantity_needed,
            metric_unit=product.default_unit,
            notes=notes,
            status_state='pending'
        )
        db.session.add(new_request)
        db.session.commit()

        create_alert(
            alert_type='new_procurement_request',
            message=f'New request from "{shelter.shelter_name}": {quantity_needed} {product.default_unit} of {product.name}.',
            shelter_id=shelter_id
        )

        flash('Procurement request submitted.', 'success')
        return redirect(url_for('field.procurement_list'))

    return render_template('field_officer/create_procurement.html',
                           shelters=my_shelters,
                           products=products)

@field_bp.route('/procurement/list')
@login_required
@role_required('field_officer')
@active_required
def procurement_list():
    my_shelters = Shelter.query.filter_by(
        created_by_id=current_user.id,
        status='active'
    ).all()

    shelter_ids = [s.id for s in my_shelters]
    requests = ProcurementRequest.query.filter(
        ProcurementRequest.origin_shelter_id.in_(shelter_ids)
    ).order_by(ProcurementRequest.created_at.desc()).all()

    return render_template('field_officer/procurement_list.html',
                           requests=requests,
                           shelters=my_shelters)


@field_bp.route('/procurement/fulfill/<int:request_id>', methods=['GET', 'POST'])
@login_required
@role_required('field_officer')
@active_required
def mark_fulfilled(request_id):
    proc_request = ProcurementRequest.query.get_or_404(request_id)

    if proc_request.status_state != 'dispatched':
        flash('Only dispatched requests can be marked as received.', 'warning')
        return redirect(url_for('field.procurement_list'))

    if request.method == 'POST':
        received_qty = int(request.form.get('received_quantity', proc_request.quantity_needed))
        proc_request.received_quantity = received_qty
        proc_request.status_state = 'fulfilled'

        # Auto-update shelter inventory
        existing_item = ShelterInventory.query.filter_by(
            shelter_id=proc_request.origin_shelter_id,
            item_name=proc_request.requested_sku
        ).first()

        if existing_item:
            existing_item.quantity += received_qty
        else:
            new_item = ShelterInventory(
                shelter_id=proc_request.origin_shelter_id,
                item_name=proc_request.requested_sku,
                quantity=received_qty,
                threshold=10,
                metric_unit=proc_request.metric_unit
            )
            db.session.add(new_item)

        db.session.commit()
        flash(f'Received {received_qty} {proc_request.metric_unit} of {proc_request.requested_sku}. Shelter inventory updated.', 'success')
        return redirect(url_for('field.procurement_list'))

    return render_template('field_officer/confirm_received.html', proc=proc_request)


@field_bp.route('/citizens/register', methods=['GET', 'POST'])
@login_required
@role_required('field_officer')
@active_required
def register_citizen_to_shelter():
    shelters = Shelter.query.filter_by(status='active').filter(Shelter.created_by_id == current_user.id).all()
    if request.method == 'POST':
        shelter_id = request.form.get('shelter_id')
        full_name = request.form.get('full_name')
        identification_number = request.form.get('identification_number')
        phone_number = request.form.get('phone_number')
        address = request.form.get('address')
        notes = request.form.get('notes')

        profile = Beneficiary.query.filter_by(identification_number=identification_number).first()
        if not profile:
            profile = Beneficiary(
                identification_number=identification_number,
                full_name=full_name,
                is_verified=False,
                created_at=db.func.now()
            )
            db.session.add(profile)
        profile.full_name = full_name
        profile.is_verified = False
        profile.user_id = None
        db.session.flush()

        registration = ShelterRegistrationRequest(
            citizen_user_id=None,
            shelter_id=int(shelter_id),
            full_name=full_name,
            identification_number=identification_number,
            phone_number=phone_number,
            address=address,
            notes=notes,
            status='pending',
            created_by_role='field_officer',
            created_by_id=current_user.id
        )
        db.session.add(registration)
        db.session.commit()
        flash('Citizen registration request has been submitted for government verification.', 'success')
        return redirect(url_for('field.dashboard'))

    return render_template('field_officer/register_citizen.html', shelters=shelters)