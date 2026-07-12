from app.extensions import db
from datetime import datetime

class Alert(db.Model):
    __tablename__ = 'alerts'

    id = db.Column(db.Integer, primary_key=True)
    alert_type = db.Column(
    db.Enum('low_shelter_stock', 'low_warehouse_stock', 'shelter_full', 'new_procurement_request',
            name='alert_type_enum'),
    nullable=False
)
    message = db.Column(db.String(255), nullable=False)
    shelter_id = db.Column(db.Integer, db.ForeignKey('shelters.id'), nullable=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    shelter = db.relationship('Shelter', backref='alerts')
    warehouse = db.relationship('Warehouse', backref='alerts')

    def __repr__(self):
        return f'<Alert {self.alert_type} | read: {self.is_read}>'