import os
from dotenv import load_dotenv

load_dotenv()  # Reads your .env file automatically

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-later')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///sahananeth_local.db'

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')

# This lets you switch modes by changing one word
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}