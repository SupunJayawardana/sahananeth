from app.extensions import db
from app.models.alert import Alert


def create_alert(alert_type, message, shelter_id=None, warehouse_id=None):
    """Creates a new alert in the database."""
    alert = Alert(
        alert_type=alert_type,
        message=message,
        shelter_id=shelter_id,
        warehouse_id=warehouse_id
    )
    db.session.add(alert)
    db.session.commit()


def check_shelter_inventory_alerts(shelter_inventory_item):
    """Call this whenever shelter inventory is updated."""
    if shelter_inventory_item.is_low:
        create_alert(
            alert_type='low_shelter_stock',
            message=f'Low stock: {shelter_inventory_item.item_name} at shelter #{shelter_inventory_item.shelter_id} — only {shelter_inventory_item.quantity} {shelter_inventory_item.metric_unit} remaining.',
            shelter_id=shelter_inventory_item.shelter_id
        )


def check_warehouse_stock_alerts(inventory_stock_item):
    """Call this whenever warehouse inventory is updated."""
    if inventory_stock_item.quantity_available <= 10:
        create_alert(
            alert_type='low_warehouse_stock',
            message=f'Low stock: {inventory_stock_item.sku_name} at warehouse #{inventory_stock_item.warehouse_id} — only {inventory_stock_item.quantity_available} {inventory_stock_item.metric_unit} remaining.',
            warehouse_id=inventory_stock_item.warehouse_id
        )


def get_unread_alerts():
    return Alert.query.filter_by(is_read=False).order_by(Alert.created_at.desc()).all()


def get_all_alerts():
    return Alert.query.order_by(Alert.created_at.desc()).limit(50).all()


def mark_all_read():
    Alert.query.filter_by(is_read=False).update({'is_read': True})
    db.session.commit()