# app/__init__.py
from __future__ import annotations

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from cryptography.fernet import Fernet
from config import Config

# ── extensiones ────────────────────────────────────────────
db      = SQLAlchemy()
migrate = Migrate()
jwt     = JWTManager()


def create_app(config_obj: type | object = Config) -> Flask:
    """
    Application Factory.
    Devuelve una instancia de Flask ya configurada.
    """
    app = Flask(__name__)
    app.config.from_object(config_obj)

    # ── claves y seguridad ────────────────────────────────
    enc_key = app.config.get("ENCRYPTION_KEY")
    if not enc_key:
        raise RuntimeError("ENCRYPTION_KEY no definida")
    app.config["FERNET"] = Fernet(enc_key.encode())

    app.config.setdefault(
        "JWT_SECRET_KEY",
        os.getenv("JWT_SECRET_KEY", "dev-jwt-secret")
    )

    # ── inicializar extensiones ───────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # ── registrar blueprints ──────────────────────────────
    from app.routes.main import main                       # /
    from app.routes.auth import bp as auth_bp              # /auth/…
    app.register_blueprint(main)
    app.register_blueprint(auth_bp)

    return app