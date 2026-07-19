import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()  # Reads your .env file automatically

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-later')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Session management ---
    # "Remember me" sessions last this long; regular sessions end when the
    # browser closes (Flask-Login's default without remember=True).
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)
    REMEMBER_COOKIE_DURATION = timedelta(days=14)

    # --- Telegram bot integration ---
    # Get a token from @BotFather on Telegram. Leave unset to run the app
    # with the bot integration fully disabled (notifications become no-ops).
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_BOT_USERNAME = os.environ.get('TELEGRAM_BOT_USERNAME', '')  # e.g. 'SahananethBot', no leading @
    # Shared secret Telegram sends back in a header on every webhook POST,
    # so /telegram/webhook/<this value> can't be guessed/spoofed.
    TELEGRAM_WEBHOOK_SECRET = os.environ.get('TELEGRAM_WEBHOOK_SECRET', 'dev-webhook-secret-change-later')

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///sahananeth_local.db'

class ProductionConfig(Config):
    DEBUG = False
    # Render gives DATABASE_URL starting with postgres://
    # SQLAlchemy needs postgresql://
    _db_url = os.environ.get('DATABASE_URL', '')
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _db_url or 'sqlite:///sahananeth_local.db'

# This lets you switch modes by changing one word
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': ProductionConfig
}