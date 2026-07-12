from app.extensions import db
from datetime import datetime

class WarehouseAssignment(db.Model):
    __tablename__ = 'warehouse_assignments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    user = db.relationship('User', foreign_keys=[user_id], backref='warehouse_assignments')
    warehouse = db.relationship('Warehouse', back_populates='assignments')
    assigned_by = db.relationship('User', foreign_keys=[assigned_by_id])

    def __repr__(self):
        return f'<Assignment user={self.user_id} warehouse={self.warehouse_id}>'