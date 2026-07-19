from app.extensions import db
from datetime import datetime


class CheckIn(db.Model):
    """
    One row per "are you safe?" broadcast. Reuses the same targeting shape
    as Notification/notify_segment (roles + country/region/city/shelter),
    but — unlike a plain announcement — tracks who actually responded and
    how, via CheckInResponse below.
    """
    __tablename__ = 'checkins'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    criteria_json = db.Column(db.Text, nullable=True)
    sent_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notification_id = db.Column(db.Integer, db.ForeignKey('notifications.id'), nullable=True)

    sent_by = db.relationship('User', backref='sent_checkins')
    notification = db.relationship('Notification', backref='checkin')
    responses = db.relationship('CheckInResponse', backref='checkin', cascade='all, delete-orphan')

    @property
    def target_count(self):
        return len(self.responses)

    @property
    def responded_count(self):
        return sum(1 for r in self.responses if r.status != 'pending')

    @property
    def safe_count(self):
        return sum(1 for r in self.responses if r.status == 'safe')

    @property
    def need_help_count(self):
        return sum(1 for r in self.responses if r.status == 'need_help')

    def __repr__(self):
        return f'<CheckIn {self.title!r} ({self.responded_count}/{self.target_count} responded)>'


class CheckInResponse(db.Model):
    """
    One row per recipient of a CheckIn, created up front (status='pending')
    for everyone in the target audience so "who has NOT responded" is a
    simple query, not an absence-of-evidence problem.
    """
    __tablename__ = 'checkin_responses'

    id = db.Column(db.Integer, primary_key=True)
    checkin_id = db.Column(db.Integer, db.ForeignKey('checkins.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(
        db.Enum('pending', 'safe', 'need_help', name='checkin_response_status_enum'),
        default='pending', nullable=False
    )
    responded_at = db.Column(db.DateTime, nullable=True)
    # Location at the moment they responded, if shared again — may differ
    # from their profile location, which matters most during a disaster.
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    user = db.relationship('User', backref='checkin_responses')

    def __repr__(self):
        return f'<CheckInResponse user={self.user_id} status={self.status}>'
