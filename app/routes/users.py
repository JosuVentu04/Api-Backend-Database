from flask import Blueprint, request, jsonify, current_app,redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import threading
from app.models import Empleado, db
from app.utils import generate_email_change_token, confirm_email_change_token, send_email

bp = Blueprint("users", __name__, url_prefix="/users")

# Función para enviar email en hilo con contexto Flask bien gestionado
def send_email_thread(app, subject, html_body, to):
    with app.app_context():
        send_email(subject, html_body, to)

@bp.post("/solicitar-cambio-correo")
@jwt_required()
def solicitar_cambio_correo():
    user_id = get_jwt_identity()
    nuevo_correo = request.json.get("nuevo_correo")
    if not nuevo_correo:
        return jsonify({"error": "Nuevo correo es requerido"}), 400

    empleado = Empleado.query.get_or_404(user_id)
    if nuevo_correo == empleado.correo:
        return jsonify({"error": "El nuevo correo es igual al actual"}), 400

    existente = Empleado.query.filter_by(correo=nuevo_correo).first()
    if existente:
        return jsonify({"error": "Correo ya en uso"}), 400

    token_antiguo = generate_email_change_token(empleado.correo, "old")
    token_nuevo = generate_email_change_token(nuevo_correo, "new")
    expiracion = datetime.utcnow() + timedelta(hours=48)

    empleado.correo_pendiente = nuevo_correo
    empleado.correo_token_antiguo = token_antiguo
    empleado.correo_token_nuevo = token_nuevo
    empleado.correo_antiguo_confirmado = False
    empleado.correo_nuevo_confirmado = False
    empleado.correo_token_expira = expiracion
    db.session.commit()

    # Links generados con url_for para coherencia
    link_antiguo = url_for("users.confirmar_email_antiguo", token=token_antiguo, _external=True)
    current_app.logger.info("LINK DEV ➜ %s", link_antiguo)
    link_nuevo = url_for("users.confirmar_email_nuevo", token=token_nuevo, _external=True)
    

    html_antiguo = (
        f"<p>Hola {empleado.nombre}, haz clic para verificar tu correo antiguo:</p>"
        f'<p><a href="{link_antiguo}">Verificar correo antiguo</a></p>'
    )
    current_app.logger.info("LINK DEV ➜ %s", link_nuevo)
    html_nuevo = (
        f"<p>Hola {empleado.nombre}, haz clic para verificar tu nuevo correo:</p>"
        f'<p><a href="{link_nuevo}">Verificar nuevo correo</a></p>'
    )

    try:
        app = current_app._get_current_object()
        # Usar threading con contexto Flask para evitar RuntimeError
        threading.Thread(target=send_email_thread, args=
        (   app,
            "Confirma cambio de correo",
            html_antiguo,
            empleado.correo
        )).start()

        threading.Thread(target=send_email_thread, args=(
            app,
            "Confirma tu nuevo correo",
            html_nuevo,
            nuevo_correo
        )).start()

    except Exception as e:
        current_app.logger.error(f"Error enviando correos de confirmación: {e}")
        return jsonify({"error": "No se pudo enviar el correo de verificación, intenta más tarde."}), 500

    return jsonify({"msg": "Se enviaron correos de verificación a ambas direcciones."}), 200


@bp.get("/confirmar-email-antiguo/<token>")
def confirmar_email_antiguo(token):
    correo = confirm_email_change_token(token, "old")
    if not correo:
        url = f"{current_app.config['DEV_FRONTEND_URL']}/correo-verificado?status=invalid"
        return redirect(url, 302)

    empleado = Empleado.query.filter_by(correo=correo).first()
    if not empleado or empleado.correo_token_antiguo != token:
        url = f"{current_app.config['DEV_FRONTEND_URL']}/correo-verificado?status=invalid"
        return redirect(url, 302)

    empleado.correo_antiguo_confirmado = True

    if empleado.correo_nuevo_confirmado:
        empleado.correo = empleado.correo_pendiente
        # Limpia campos temporales
        empleado.correo_pendiente = None
        empleado.correo_token_antiguo = None
        empleado.correo_token_nuevo = None
        empleado.correo_antiguo_confirmado = False
        empleado.correo_nuevo_confirmado = False
        empleado.correo_token_expira = None

    db.session.commit()
    url = f"{current_app.config['DEV_FRONTEND_URL']}/correo-verificado?status=ok"
    return redirect(url, 302)


@bp.get("/confirmar-email-nuevo/<token>")
def confirmar_email_nuevo(token):
    correo = confirm_email_change_token(token, "new")
    if not correo:
        url = f"{current_app.config['DEV_FRONTEND_URL']}/correo-verificado?status=invalid"
        return redirect(url, 302)

    empleado = Empleado.query.filter_by(correo_pendiente=correo).first()
    if not empleado or empleado.correo_token_nuevo != token:
        url = f"{current_app.config['DEV_FRONTEND_URL']}/correo-verificado?status=invalid"
        return redirect(url, 302) 

    empleado.correo_nuevo_confirmado = True

    if empleado.correo_antiguo_confirmado:
        empleado.correo = empleado.correo_pendiente
        empleado.correo_pendiente = None
        empleado.correo_token_antiguo = None
        empleado.correo_token_nuevo = None
        empleado.correo_antiguo_confirmado = False
        empleado.correo_nuevo_confirmado = False
        empleado.correo_token_expira = None

    db.session.commit()
    url = f"{current_app.config['DEV_FRONTEND_URL']}/correo-verificado?status=ok"
    return redirect(url, 302)


@bp.put("/perfil")
@jwt_required()
def actualizar_perfil():
    
    user_id = get_jwt_identity()
    datos = request.get_json()

    empleado = Empleado.query.get_or_404(user_id)

    # Actualiza solo campos permitidos. NO permitimos cambiar correo aquí para mantener flujo seguro
    if "nombre" in datos:
        empleado.nombre = datos["nombre"]

    # Puedes agregar campos adicionales seguros aquí.

    db.session.commit()

    return jsonify({
        "msg": "Perfil actualizado correctamente",
        "empleado": empleado.serialize()
    }), 200