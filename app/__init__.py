from flask import Flask
from config import config
from app.extensions import db, migrate, login_manager

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Register blueprints
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # Load models so Flask-Migrate can see them
    with app.app_context():
        from app import models  # noqa: F401

    return app