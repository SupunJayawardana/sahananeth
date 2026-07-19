from flask import Flask, render_template, redirect, url_for
from flask_login import current_user
from config import config
from app.extensions import db, migrate, login_manager

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.role_level == 'citizen':
                return redirect(url_for('citizen.dashboard'))
            return redirect(url_for('auth.dashboard'))
        return render_template('index.html')

    from app import models

    from app.routes.auth import auth_bp
    from app.routes.citizen import citizen_bp
    from app.routes.field_officer import field_bp
    from app.routes.gov_officer import gov_bp
    from app.routes.super_admin import admin_bp
    from app.routes.warehouse_manager import warehouse_bp
    from app.routes.bot import bot_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(citizen_bp, url_prefix='/citizen')
    app.register_blueprint(field_bp, url_prefix='/field')
    app.register_blueprint(gov_bp, url_prefix='/gov')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(warehouse_bp, url_prefix='/warehouse')
    app.register_blueprint(bot_bp, url_prefix='/telegram')
    app.register_blueprint(api_bp, url_prefix='/api')

    return app