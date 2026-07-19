from app.extensions import db
from datetime import datetime

class Shelter(db.Model):
    __tablename__ = 'shelters'

    id = db.Column(db.Integer, primary_key=True)
    shelter_name = db.Column(db.String(150), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    maximum_capacity = db.Column(db.Integer, nullable=False)
    current_occupancy_count = db.Column(db.Integer, default=0)
    address = db.Column(db.String(255), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    region = db.Column(db.String(100), nullable=True)   # state / province / district
    city = db.Column(db.String(100), nullable=True)
    status = db.Column(
    db.Enum('pending_approval', 'active', 'inactive',
            name='shelter_status_enum'),
    default='pending_approval',
    nullable=False
)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_shelters')
    approved_by = db.relationship('User', foreign_keys=[approved_by_id], backref='approved_shelters')
    inventory_items = db.relationship('ShelterInventory', backref='shelter', cascade='all, delete-orphan')

    @property
    def is_full(self):
        return self.current_occupancy_count >= self.maximum_capacity

    @property
    def available_slots(self):
        return self.maximum_capacity - self.current_occupancy_count

    def __repr__(self):
        return f'<Shelter {self.shelter_name} | {self.status}>'


class ShelterInventory(db.Model):
    __tablename__ = 'shelter_inventory'

    id = db.Column(db.Integer, primary_key=True)
    shelter_id = db.Column(db.Integer, db.ForeignKey('shelters.id'), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    threshold = db.Column(db.Integer, default=10)  # Alert when below this
    metric_unit = db.Column(db.String(30), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def is_low(self):
        return self.quantity <= self.threshold

    def __repr__(self):
        return f'<ShelterInventory {self.item_name} | {self.quantity} {self.metric_unit}>'