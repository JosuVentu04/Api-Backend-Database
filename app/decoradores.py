from functools import wraps
from flask import abort, current_app
from flask_jwt_extended import jwt_required, get_jwt

def roles_required(roles_permitidos):
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorator(*args, **kwargs):
            claims = get_jwt()
            current_app.logger.info(f"Payload completo JWT: {claims}")
            rol_usuario = claims.get("role", "").upper()
            current_app.logger.info(f"Rol extraído del JWT: {rol_usuario}")
            if rol_usuario not in roles_permitidos:
                abort(403)
            return fn(*args, **kwargs)
        return decorator
    return wrapper