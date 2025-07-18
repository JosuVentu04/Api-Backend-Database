from flask import Blueprint, request, url_for, jsonify, current_app
from flask_jwt_extended import create_access_token
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from app.utils import generate_email_token, confirm_email_token, send_email
from app.models import Empleado, db

bp = Blueprint("auth", __name__, url_prefix="/auth")   # ← prefijo único

# ────────────────────────────
# 1) Enviar link de verificación
# ────────────────────────────
@bp.post("/enviar-verificacion")
def enviar_verificacion():
    data = request.get_json() or {}
    correo = data.get("correo")
    if not correo:
        return {"error": "correo requerido"}, 400

    empleado = Empleado.query.filter_by(correo=correo).first()
    if not empleado:
        return {"error": "usuario no encontrado"}, 404

    token = generate_email_token(correo)
    link  = url_for("auth.confirmar_correo", token=token, _external=True)
    current_app.logger.info("LINK DEV ➜ %s", link)   # visible en consola

    html = (
        f"<p>Hola {empleado.nombre}, haz clic para verificar tu correo:</p>"
        f'<p><a href="{link}">Verificar</a></p>'
    )

    try:
        send_email("Verifica tu correo", html, correo)
    except Exception:
        current_app.logger.exception("Error enviando e-mail")
        return {"error": "no se pudo enviar el correo"}, 500

    return {"msg": "e-mail de verificación enviado"}, 202


# ────────────────────────────
# 2) Confirmar correo
# ────────────────────────────
@bp.get("/confirmar-correo/<token>")
def confirmar_correo(token):
    correo = confirm_email_token(token)
    if not correo:
        return {"error": "token inválido o expirado"}, 400

    empleado = Empleado.query.filter_by(correo=correo).first()
    if not empleado:
        return {"error": "usuario no encontrado"}, 404
    if empleado.is_verified:                       # ← usa el campo real
        return {"msg": "ya estaba verificado"}, 200

    empleado.is_verified = True
    empleado.fecha_verificacion = datetime.utcnow()
    db.session.commit()

    return {"msg": "correo verificado con éxito"}, 200



# ────────────────────────────
# 3) Login protegido
# ────────────────────────────
@bp.post("/login")
def login():
    data = request.get_json() or {}
    correo   = data.get("correo")
    password = data.get("password")

    if not correo or not password:
        return {"msg": "correo y password requeridos"}, 400

    emp = Empleado.query.filter_by(correo=correo).first()
    if not emp or not emp.check_password(password):
        return {"msg": "credenciales inválidas"}, 401
    if not emp.is_verified:
        return {"msg": "verifica tu correo antes de iniciar sesión"}, 403

    token = create_access_token(identity=emp.id)
    return {"access_token": token}, 200