from app.extensions import db
from datetime import datetime

class ProcurementRequest(db.Model):
    __tablename__ = 'procurement_requests'

    id = db.Column(db.Integer, primary_key=True)
    origin_shelter_id = db.Column(db.Integer, db.ForeignKey('shelters.id'), nullable=False)
    requested_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    requested_sku = db.Column(db.String(100), nullable=False)
    quantity_needed = db.Column(db.Integer, nullable=False)
    metric_unit = db.Column(db.String(30), nullable=False)
    notes = db.Column(db.String(255), nullable=True)
    status_state = db.Column(
    db.Enum('pending', 'approved', 'dispatched', 'fulfilled', 'rejected',
            name='procurement_status_enum'),
    default='pending'
)
    received_quantity = db.Column(db.Integer, nullable=True)
    fulfilled_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    shelter = db.relationship('Shelter', backref='procurement_requests')
    requested_by = db.relationship('User', backref='procurement_requests')
    fulfilled_warehouse = db.relationship('Warehouse', backref='fulfilled_requests')

    def __repr__(self):
        return f'<Request {self.requested_sku} x{self.quantity_needed} | {self.status_state}>'