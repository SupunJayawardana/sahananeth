from app.extensions import db
from datetime import datetime, timedelta
import secrets

class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    code = db.Column(db.String(12), nullable=False)   # short code, easy to type from Telegram
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref='password_reset_tokens')

    @staticmethod
    def generate(user_id, ttl_minutes=15):
        code = f'{secrets.randbelow(1000000):06d}'
        return PasswordResetToken(
            user_id=user_id,
            code=code,
            expires_at=datetime.utcnow() + timedelta(minutes=ttl_minutes)
        )

    @property
    def is_valid(self):
        return self.used_at is None and datetime.utcnow() < self.expires_at

    def __repr__(self):
        return f'<PasswordResetToken user={self.user_id} used={self.used_at is not None}>'
