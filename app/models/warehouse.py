from app.extensions import db
from datetime import datetime

class Warehouse(db.Model):
    __tablename__ = 'warehouses'

    id = db.Column(db.Integer, primary_key=True)
    warehouse_name = db.Column(db.String(150), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    address = db.Column(db.String(255), nullable=True)
    status = db.Column(
        db.Enum('pending_approval', 'active', 'inactive',
                name='warehouse_status_enum'),
        default='pending_approval',
        nullable=False
    )
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    created_by = db.relationship('User', foreign_keys=[created_by_id],
                                 backref='created_warehouses')
    approved_by = db.relationship('User', foreign_keys=[approved_by_id],
                                  backref='approved_warehouses')
    inventory = db.relationship('InventoryStock', backref='warehouse',
                                cascade='all, delete-orphan')
    assignments = db.relationship('WarehouseAssignment', back_populates='warehouse',
                              cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Warehouse {self.warehouse_name} | {self.status}>'


class InventoryStock(db.Model):
    __tablename__ = 'inventory_stock'

    id = db.Column(db.Integer, primary_key=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    sku_name = db.Column(db.String(100), nullable=False)
    quantity_available = db.Column(db.Integer, default=0)
    metric_unit = db.Column(db.String(30), nullable=False)
    threshold = db.Column(db.Integer, default=10)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    @property
    def is_low(self):
        return self.quantity_available <= self.threshold

    def __repr__(self):
        return f'<Stock {self.sku_name} | {self.quantity_available} {self.metric_unit}>'