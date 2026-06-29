from app.extensions import db

class Shelter(db.Model):
    __tablename__ = 'shelters'

    id = db.Column(db.Integer, primary_key=True)
    shelter_name = db.Column(db.String(120), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    maximum_capacity = db.Column(db.Integer, nullable=False)
    current_occupancy_count = db.Column(db.Integer, default=0)

    # Relationship — one shelter has many beneficiaries
    beneficiaries = db.relationship('Beneficiary', backref='shelter', lazy=True)

    @property
    def is_full(self):
        return self.current_occupancy_count >= self.maximum_capacity

    def __repr__(self):
        return f'<Shelter {self.shelter_name} | {self.current_occupancy_count}/{self.maximum_capacity}>'


class Beneficiary(db.Model):
    __tablename__ = 'beneficiaries'

    id = db.Column(db.Integer, primary_key=True)
    identification_number = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    allocated_shelter_id = db.Column(db.Integer, db.ForeignKey('shelters.id'), nullable=True)

    def __repr__(self):
        return f'<Beneficiary {self.full_name} | Verified: {self.is_verified}>'