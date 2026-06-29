from app.extensions import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role_level = db.Column(db.Enum('citizen', 'field_officer', 'gov_officer'), nullable=False)
    assigned_node_id = db.Column(db.Integer, nullable=True)  # For field officers → shelter ID

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username} | {self.role_level}>'

# Flask-Login needs this to reload user from session
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))