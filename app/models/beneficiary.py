from app.extensions import db
from datetime import datetime

class Beneficiary(db.Model):
    __tablename__ = 'beneficiaries'

    id = db.Column(db.Integer, primary_key=True)
    identification_number = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    allocated_shelter_id = db.Column(db.Integer, db.ForeignKey('shelters.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    shelter = db.relationship('Shelter', backref='beneficiaries')
    user = db.relationship('User', backref='beneficiary_profile')

    def __repr__(self):
        return f'<Beneficiary {self.full_name} | Verified: {self.is_verified}>'