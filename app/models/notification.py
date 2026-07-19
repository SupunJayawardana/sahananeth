from app.extensions import db
from datetime import datetime

class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(
        db.Enum('auto_alert', 'announcement', name='notification_category_enum'),
        nullable=False
    )
    urgency = db.Column(
        db.Enum('info', 'warning', 'critical', name='notification_urgency_enum'),
        default='info', nullable=False
    )
    title = db.Column(db.String(150), nullable=True)
    message = db.Column(db.String(1000), nullable=False)
    # Free-form record of what criteria were used to build the audience,
    # e.g. {"roles": ["citizen"], "country": "Sri Lanka", "region": "Western"}
    criteria_json = db.Column(db.Text, nullable=True)
    sent_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sent_by = db.relationship('User', backref='sent_notifications')
    deliveries = db.relationship('NotificationDelivery', backref='notification',
                                  cascade='all, delete-orphan')

    @property
    def delivered_count(self):
        return sum(1 for d in self.deliveries if d.status == 'sent')

    @property
    def failed_count(self):
        return sum(1 for d in self.deliveries if d.status == 'failed')

    @property
    def skipped_count(self):
        return sum(1 for d in self.deliveries if d.status == 'skipped_not_linked')

    def __repr__(self):
        return f'<Notification {self.category} "{self.title}">'


class NotificationDelivery(db.Model):
    __tablename__ = 'notification_deliveries'

    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(db.Integer, db.ForeignKey('notifications.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(
        db.Enum('sent', 'failed', 'skipped_not_linked', name='delivery_status_enum'),
        nullable=False
    )
    error_message = db.Column(db.String(255), nullable=True)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='notification_deliveries')

    def __repr__(self):
        return f'<NotificationDelivery user={self.user_id} status={self.status}>'
