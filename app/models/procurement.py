from app.extensions import db
from datetime import datetime

class ProcurementRequest(db.Model):
    __tablename__ = 'procurement_requests'

    id = db.Column(db.Integer, primary_key=True)
    origin_shelter_id = db.Column(db.Integer, db.ForeignKey('shelters.id'), nullable=False)
    requested_sku = db.Column(db.String(120), nullable=False)
    quantity_needed = db.Column(db.Integer, nullable=False)
    status_state = db.Column(
        db.Enum('pending', 'approved', 'fulfilled', 'rejected',
                name='procurement_status_enum'),
        default='pending'
    )
    fulfilled_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Request {self.requested_sku} | {self.status_state}>'