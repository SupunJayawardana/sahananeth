from app.extensions import db
from datetime import datetime

class CitizenAidRequest(db.Model):
    """
    A citizen's own plain-language request for help (e.g. submitted via the
    Telegram bot without needing a Field Officer to raise it on their behalf).
    Deliberately simpler than ProcurementRequest — no SKU/warehouse
    bookkeeping, just "here's what I need and where I am" for a Field
    Officer or Gov Officer to triage.
    """
    __tablename__ = 'citizen_aid_requests'

    id = db.Column(db.Integer, primary_key=True)
    citizen_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    shelter_id = db.Column(db.Integer, db.ForeignKey('shelters.id'), nullable=True)
    description = db.Column(db.String(500), nullable=False)
    country = db.Column(db.String(100), nullable=True)
    region = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    status = db.Column(
        db.Enum('pending', 'in_progress', 'resolved', name='aid_request_status_enum'),
        default='pending', nullable=False
    )
    resolved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    citizen = db.relationship('User', foreign_keys=[citizen_user_id], backref='aid_requests')
    shelter = db.relationship('Shelter', backref='citizen_aid_requests')
    resolved_by = db.relationship('User', foreign_keys=[resolved_by_id])

    def __repr__(self):
        return f'<CitizenAidRequest {self.citizen_user_id} | {self.status}>'
