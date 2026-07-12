from app.extensions import db
from datetime import datetime


class ShelterRegistrationRequest(db.Model):
    __tablename__ = 'shelter_registration_requests'

    id = db.Column(db.Integer, primary_key=True)
    citizen_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    shelter_id = db.Column(db.Integer, db.ForeignKey('shelters.id'), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    identification_number = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(30), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.String(255), nullable=True)
    status = db.Column(
        db.Enum('pending', 'approved', 'rejected', name='registration_status_enum'),
        default='pending',
        nullable=False
    )
    created_by_role = db.Column(db.String(50), nullable=False, default='citizen')
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    citizen = db.relationship('User', foreign_keys=[citizen_user_id], backref='shelter_registration_requests')
    shelter = db.relationship('Shelter', backref='registration_requests')
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_shelter_requests')
    reviewed_by = db.relationship('User', foreign_keys=[reviewed_by_id], backref='reviewed_shelter_requests')

    def __repr__(self):
        return f'<ShelterRegistrationRequest {self.full_name} | {self.status}>'
