from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# Create instances here, but don't attach to app yet
# They get attached in create_app() to avoid circular imports
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

login_manager.login_view = 'auth.login'  # Redirect here if not logged in
login_manager.login_message_category = 'info'