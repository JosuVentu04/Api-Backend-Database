import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
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


    

