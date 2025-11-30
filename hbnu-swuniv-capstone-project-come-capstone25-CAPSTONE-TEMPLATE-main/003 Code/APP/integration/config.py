import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "medicall_key")
    
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt_key")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_ALGORITHM = "HS256"

class DevelopmentConfig(Config):
    DEBUG = True
    DATABASE_URL = os.getenv('DEV_DATABASE_URL', 
        "mysql+aiomysql://root:0164@localhost:3306/medicall")

class ProductionConfig(Config):
    DEBUG = False
    DATABASE_URL = os.getenv('DATABASE_URL', 
        "mysql+aiomysql://root:0164@localhost:3306/medicall")

class TestingConfig(Config):
    TESTING = True
    DATABASE_URL = "sqlite+aiosqlite:///:memory:"

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 