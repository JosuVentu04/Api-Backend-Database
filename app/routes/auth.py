from flask import Blueprint, request, jsonify, current_app, redirect, url_for
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from app.utils import generate_email_token, confirm_email_token, send_email
from app.models import Empleado, db
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

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
@bp.get("/confirmar-correo/<path:token>")
def confirmar_correo(token):
    # 1. Validar el token ---------------------------------------------
    correo = confirm_email_token(token)            # None si expira / inválido
    if not correo:                                 # redirige al frontend
        url = f"{current_app.config['DEV_FRONTEND_URL']}/correo-verificado?status=invalid"
        return redirect(url, 302)

    # 2. Marcar la cuenta como verificada ------------------------------
    emp = Empleado.query.filter_by(correo=correo).first_or_404()
    if not emp.is_verified:
        emp.is_verified = True
        emp.fecha_verificacion = db.func.now()
        db.session.commit()

    # 3. Redirigir con éxito -------------------------------------------
    url = f"{current_app.config['DEV_FRONTEND_URL']}/correo-verificado?status=ok"
    return redirect(url, 302)


# ────────────────────────────
# 3) Login protegido
# ────────────────────────────
@bp.post("/login")
def login():
    data = request.get_json() or {}
    correo   = data.get("correo")
    password = data.get("password")
    sucursal_id = data.get("sucursal_id")

    if not correo or not password:
        return {"msg": "correo y password requeridos"}, 400

    emp = Empleado.query.filter_by(correo=correo, sucursal_id=sucursal_id).first()
    if not emp or not emp.check_password(password):
        return {"msg": "Correo, contraseña o sucursal inválida"}, 401
    if not emp.is_verified:
        return {"msg": "verifica tu correo antes de iniciar sesión"}, 403

    token = create_access_token(identity=str(emp.id))
    
    print(sucursal_id)
    return {"access_token": token}, 200

@bp.get("/me")
@jwt_required()                                              # requiere JWT en el header
def me():
    """
    Devuelve el empleado asociado al JWT:
        Authorization: Bearer <access_token>
    """
    emp_id = get_jwt_identity()                              # valor que grabaste en create_access_token
    emp = Empleado.query.get_or_404(emp_id)                  # 404 si el id no existe
    # método serialize() ya lo usas en /empleados
    return jsonify(emp.serialize()), 200
