from app.extensions import db
from datetime import datetime, timedelta
import secrets

class TelegramLinkToken(db.Model):
    __tablename__ = 'telegram_link_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref='telegram_link_tokens')

    @staticmethod
    def generate(user_id, ttl_minutes=30):
        token = secrets.token_urlsafe(16)
        return TelegramLinkToken(
            user_id=user_id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(minutes=ttl_minutes)
        )

    @property
    def is_valid(self):
        return self.used_at is None and datetime.utcnow() < self.expires_at

    def __repr__(self):
        return f'<TelegramLinkToken user={self.user_id} used={self.used_at is not None}>'
