from flask import Flask
from config import config
from app.extensions import db, migrate, login_manager

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from app import models

    from app.routes.auth import auth_bp
    from app.routes.citizen import citizen_bp
    from app.routes.field_officer import field_bp
    from app.routes.gov_officer import gov_bp
    from app.routes.super_admin import admin_bp
    from app.routes.warehouse_manager import warehouse_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(citizen_bp, url_prefix='/citizen')
    app.register_blueprint(field_bp, url_prefix='/field')
    app.register_blueprint(gov_bp, url_prefix='/gov')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(warehouse_bp, url_prefix='/warehouse')

    return app