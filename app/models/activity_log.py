from app.extensions import db
from datetime import datetime

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(
        db.Enum('auth', 'user', 'shelter', 'warehouse', 'procurement', 'alert',
                name='activity_category_enum'),
        nullable=False
    )
    description = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='activity_logs')

    def __repr__(self):
        return f'<ActivityLog {self.category} | {self.description[:30]}>'
