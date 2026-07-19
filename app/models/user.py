from app.extensions import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(150), nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role_level = db.Column(
    db.Enum('super_admin', 'gov_officer', 'field_officer', 
            'warehouse_manager', 'citizen',
            name='user_role_enum'),
    nullable=False
)
    status = db.Column(
        db.Enum('pending', 'active', 'needs_verification', 'verified', 'rejected',name='user_status_enum'),
        default='pending',
        nullable=False
    )
    assigned_node_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # --- Telegram bot integration ---
    telegram_chat_id = db.Column(db.String(64), unique=True, nullable=True)
    telegram_linked_at = db.Column(db.DateTime, nullable=True)
    notify_opt_in = db.Column(db.Boolean, default=True, nullable=False)

    # --- Location (free-text so the system isn't tied to one country's
    #     administrative divisions — works for any country/region/city) ---
    country = db.Column(db.String(100), nullable=True)
    region = db.Column(db.String(100), nullable=True)   # state / province / district
    city = db.Column(db.String(100), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active_user(self):
        return self.status in ('active', 'verified')

    @property
    def is_pending(self):
        return self.status == 'pending'

    @property
    def telegram_linked(self):
        return self.telegram_chat_id is not None

    def __repr__(self):
        return f'<User {self.username} | {self.role_level} | {self.status}>'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

