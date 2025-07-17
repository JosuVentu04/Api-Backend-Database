from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from cryptography.fernet import Fernet
from config import Config

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Verificar ENCRYPTION_KEY
    if not app.config.get('ENCRYPTION_KEY'):
        raise RuntimeError("No se encontró la clave ENCRYPTION_KEY")

    app.config['FERNET'] = Fernet(app.config['ENCRYPTION_KEY'].encode())

    db.init_app(app)
    migrate.init_app(app, db)

    from app.routes import main
    app.register_blueprint(main)

    return app