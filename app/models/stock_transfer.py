from app.extensions import db
from datetime import datetime

class StockTransfer(db.Model):
    __tablename__ = 'stock_transfers'

    id = db.Column(db.Integer, primary_key=True)
    from_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'),
                                   nullable=False)
    to_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'),
                                 nullable=False)
    sku_name = db.Column(db.String(100), nullable=False)
    metric_unit = db.Column(db.String(30), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(
        db.Enum('pending', 'dispatched', 'confirmed',
                name='transfer_status_enum'),
        default='pending',
        nullable=False
    )
    notes = db.Column(db.String(255), nullable=True)
    initiated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    confirmed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime, nullable=True)

    from_warehouse = db.relationship('Warehouse', foreign_keys=[from_warehouse_id],
                                      backref='outgoing_transfers')
    to_warehouse = db.relationship('Warehouse', foreign_keys=[to_warehouse_id],
                                    backref='incoming_transfers')
    initiated_by = db.relationship('User', foreign_keys=[initiated_by_id],
                                    backref='initiated_transfers')
    confirmed_by = db.relationship('User', foreign_keys=[confirmed_by_id],
                                    backref='confirmed_transfers')

    def __repr__(self):
        return f'<Transfer {self.sku_name} x{self.quantity} | {self.status}>'