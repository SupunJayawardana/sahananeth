from flask import Flask
from config import config
from app.extensions import db, migrate, login_manager

def create_app(config_name='default'):
    app = Flask(__name__)
    
    # Load config (development or production)
    app.config.from_object(config[config_name])
    
    # Attach extensions to this app instance
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # Register blueprints (routes) — we'll add more later
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    return app