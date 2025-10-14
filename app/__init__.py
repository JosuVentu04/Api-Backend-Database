from __future__ import annotations
import os
from flask import Flask, request, current_app, jsonify         # ← importa request para debug
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from cryptography.fernet import Fernet
from config import Config
import requests


# ── extensiones globales ───────────────────────────────
db      = SQLAlchemy()
migrate = Migrate()
jwt     = JWTManager()


def create_app(config_obj: type | object = Config) -> Flask:
    """Application Factory: devuelve una instancia de Flask configurada."""
    app = Flask(__name__)

    # 1) Cargar configuración
    app.config.from_object(config_obj)

    # 2) Seguridad
    enc_key = app.config.get("ENCRYPTION_KEY")
    if not enc_key:
        raise RuntimeError("ENCRYPTION_KEY no definida")
    app.config["FERNET"] = Fernet(enc_key.encode())

    app.config.setdefault(
        "JWT_SECRET_KEY",
        os.getenv("JWT_SECRET_KEY", "dev-jwt-secret")
    )

    # 3) CORS
    frontend_url = os.getenv('DEV_FRONTEND_URL')
    print("Frontend URL from env:", frontend_url)

# Verificar que exista
    if not frontend_url:
        raise RuntimeError("La variable DEV_FRONTEND_URL no está definida.")

# Guardarla en la configuración de Flask
    app.config['DEV_FRONTEND_URL'] = frontend_url          # prod → https://dashboard.miapp.com
    extra_dev_url = os.getenv("DEV_FRONTEND_URL")          # codespace dinámico

    allowed_origins: list[str] = []
    if frontend_url:
        allowed_origins.append(frontend_url)

    # Compatibilidad Flask 2 / Flask 3
    env_value = app.config.get("ENV", os.getenv("FLASK_ENV", "production"))

    # Desarrollo o tests
    if env_value != "production":
        if extra_dev_url:               # solo añade si existe
            allowed_origins.append(extra_dev_url)
        allowed_origins.append("http://localhost:3000")
        allowed_origins.append("http:// http://localhost:5173")

    if not allowed_origins:
        raise RuntimeError("FRONTEND_URL faltante: CORS sin origen permitido")

    print("CORS origins:", allowed_origins)   # ← log útil

    CORS(
        app,
        origins= "*",
        supports_credentials=True,
        expose_headers=["Authorization"],
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    )

    # 4) Inicializar extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    
    @jwt.unauthorized_loader
    def missing(msg):
        current_app.logger.error("JWT missing/invalid → %s", msg)
        return {"msg": msg}, 401

    @jwt.invalid_token_loader
    def invalid(msg):
        current_app.logger.error("JWT inválido → %s", msg)
        return {"msg": msg}, 422

    # 5) Registrar blueprints
    from app.routes.main import main
    from app.routes.auth import bp as auth_bp
    from app.routes.users import bp as users_bp 
    from app.routes.devices_models import dispositivos   
    from app.routes.verificacion import veriff_bp
    from app.routes.webAuth import webauthn_bp
    from app.routes.contracts import contratos_bp
    app.register_blueprint(main)
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp) 
    app.register_blueprint(dispositivos)
    app.register_blueprint(veriff_bp)
    app.register_blueprint(webauthn_bp)
    app.register_blueprint(contratos_bp)
    
    if __name__ == '__main__':
        app.run(debug=True)

    # 6) Debug opcional: muestra cada respuesta que pasa por Flask
    @app.after_request
    def debug_cors(resp):
        print(
            "→", request.method, request.path,
            "::", resp.status_code,
            ":: OriginIN =", request.headers.get("Origin"),
            ":: A-C-A-O =", resp.headers.get("Access-Control-Allow-Origin")
        )
        return resp           # ← ESTA LÍNEA ES IMPRESCINDIBLE

    return app
        
    

