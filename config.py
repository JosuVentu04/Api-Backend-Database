import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT   = int(os.getenv("MAIL_PORT", 587))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_USE_TLS  = os.getenv("MAIL_USE_TLS", "True") == "True"
    EMAIL_TOKEN_SALT = os.getenv("EMAIL_TOKEN_SALT", "verificacion-email")
    SERVER_NAME = "didactic-space-acorn-v6qxr47wv9gxhxv64-5000.app.github.dev"
    PREFERRED_URL_SCHEME = "https"
    FRONTEND_URL = "https://fictional-space-fishstick-5gxwr6p5qpppfvqj9-3000.app.github.dev/"
    DEV_FRONTEND_URL = "https://fictional-space-fishstick-5gxwr6p5qpppfvqj9-3000.app.github.dev/"
    # ────── Core ──────
    SECURITY_PASSWORD_SALT = os.getenv("SECURITY_PASSWORD_SALT", "salt-dev")

    # ────── JWT ──────
    JWT_SECRET_KEY = SECRET_KEY
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRES = 3600        # segundos

    # ────── Base de datos ──────
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///app.db")

    # ────── Mail ──────

