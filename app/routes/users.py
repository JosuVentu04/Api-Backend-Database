from flask import Blueprint, request, jsonify, current_app,redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import threading
import requests
from sqlalchemy.exc import SQLAlchemyError
from app.models import Empleado, db, EstadoUsuario, Usuario, TipoIdentificacion, Domicilio, EstadoDeuda, ContratoCompraVenta, Pago
from app.utils import generate_email_change_token, confirm_email_change_token, send_email
from app.decoradores import roles_required

users_bp = Blueprint("users", __name__, url_prefix="/users")

# Función para enviar email en hilo con contexto Flask bien gestionado
def send_email_thread(app, subject, html_body, to):
    with app.app_context():
        send_email(subject, html_body, to)

@users_bp.post("/solicitar-cambio-correo")
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


@users_bp.get("/confirmar-email-antiguo/<token>")
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


@users_bp.get("/confirmar-email-nuevo/<token>")
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



@users_bp.put("/perfil")
@roles_required({"VENDEDOR", "GERENTE", "ADMIN", "SOPORTE"})
@jwt_required()
def actualizar_perfil():
    
    user_id = get_jwt_identity()
    datos = request.get_json()

    empleado = Empleado.query.get_or_404(user_id)

    # Actualiza solo campos permitidos. NO permitimos cambiar correo aquí para mantener flujo seguro
    if "nombre" in datos:
        empleado.nombre = datos["nombre"]
    if "numero_telefonico" in datos:
        empleado.numero_telefonico = datos["numero_telefonico"]

    # Puedes agregar campos adicionales seguros aquí.

    db.session.commit()

    return jsonify({
        "msg": "Perfil actualizado correctamente",
        "empleado": empleado.serialize()
    }), 200
    
@users_bp.put("/modificar-empleado/<int:empleado_id>")
@roles_required({"VENDEDOR", "GERENTE", "ADMIN", "SOPORTE"})
@jwt_required()
def modificar_empleado(empleado_id):
    data = request.get_json() or {}

    empleado = Empleado.query.get_or_404(empleado_id)

    # 🔹 Modificar solo campos permitidos
    if "rol" in data:
        empleado.rol = data["rol"].upper()

    if "sucursal_id" in data:
        empleado.sucursal_id = data["sucursal_id"]

    if "estado_usuario" in data:
        try:
            empleado.estado_usuario = EstadoUsuario[data["estado_usuario"].upper()]
        except KeyError:
            return jsonify({"error": "Estado de usuario inválido"}), 400

    campos_permitidos = {"rol", "sucursal_id", "estado_usuario"}
    for campo in data.keys():
        if campo not in campos_permitidos:
            return jsonify({"error": f"No está permitido modificar el campo '{campo}'"}), 400

    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Error modificando empleado")
        return jsonify({"error": "Error al modificar el empleado"}), 500

    return jsonify({ 
        "msg": "Empleado modificado correctamente",
        "empleado": empleado.serialize()
    }), 200       
    
# ──────────────────────────────
# 2. CLIENTES
# ──────────────────────────────

@users_bp.post("/crear-cliente")
@jwt_required()
def crear_cliente():
    data = request.get_json() or {}

    if not data.get("primer_nombre") or not data.get("apellido_paterno") or not data.get("numero_identificacion"):
        return jsonify({"error": "Nombre, apellido y DNI son obligatorios"}), 400

    existente = Usuario.query.filter_by(numero_identificacion=data["numero_identificacion"]).first()
    if existente:
        return jsonify({"error": "DNI ya registrado"}), 400

    nuevo_cliente = Usuario(
        primer_nombre=data["primer_nombre"],
        apellido_paterno=data["apellido_paterno"],
        tipo_identificacion=TipoIdentificacion("id_card"),
        numero_identificacion=data["numero_identificacion"],
        # otros campos que tenga tu modelo Cliente
    )

    # Campos opcionales
    if "correo" in data:
        nuevo_cliente.correo = data["correo"]
    if "telefono" in data:
        nuevo_cliente.telefono = data["telefono"]
    if "direccion" in data:
        nuevo_cliente.direccion = data["direccion"]

    try:
        db.session.add(nuevo_cliente)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Error al crear cliente", "detalle": str(e)}), 500

    return jsonify({
        "msg": "Cliente creado exitosamente",
        "cliente": nuevo_cliente.serialize()
    }), 201
    
@users_bp.get("/clientes")
@jwt_required()
def listar_clientes():
    clientes = Usuario.query.all()
    resultado = [cliente.serialize() for cliente in clientes]
    return jsonify(resultado), 200

@users_bp.get("/cliente/<int:id>")
@jwt_required()
def obtener_cliente(id):
    cliente = Usuario.query.get(id)
    if not cliente:
        return jsonify({"error": "Cliente no encontrado"}), 404
    return jsonify(cliente.serialize()), 200

@users_bp.put("/editar-cliente/<int:id>")
@jwt_required()
def editar_cliente(id):
    data = request.get_json() or {}
    usuario = Usuario.query.get(id)

    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404

    # 🔹 Lista blanca de campos que se pueden modificar
    campos_permitidos = {
        "primer_nombre",
        "segundo_nombre",
        "apellido_paterno",
        "apellido_materno",
        "correo",
        "telefono",
        "direccion",
        "rfc",
        "fecha_nacimiento",
        "score_crediticio",
        "credito_aprobado",
        "estado_usuario",
    }

    # 🔹 Iterar sobre los campos del request
    for campo, valor in data.items():
        if campo in campos_permitidos:
            setattr(usuario, campo, valor)
        else:
            return jsonify({"error": f"No está permitido modificar el campo '{campo}'"}), 400

    try:
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Error actualizando usuario {id}: {e}")
        return jsonify({"error": "Error al actualizar el usuario"}), 500

    return jsonify({
        "msg": "Usuario actualizado correctamente",
        "usuario": usuario.serialize()
    }), 200

@users_bp.post("/historial-crediticio")
def historial_crediticio():
    data = request.get_json() or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id es requerido"}), 400

    usuario = Usuario.query.get(user_id)
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404

    domicilio = Domicilio.query.filter_by(usuario_id=user_id).first()
    
    #Esta parte se comenta para pruebas locales sin afectar el servicio externo
    # Se debe descomentar para uso en producción y modificar según el API real
    # de historial crediticio.
    """
     payload = {
        "primerNombre": usuario.primer_nombre or "",
        "apellidoPaterno": usuario.apellido_paterno or "",
        "apellidoMaterno": usuario.apellido_materno or "",
        "fechaNacimiento": usuario.fecha_nacimiento.isoformat() if usuario.fecha_nacimiento else "",
        "RFC": usuario.rfc or "",
        "nacionalidad": "MX",
        "domicilio": {
            "coloniaPoblacion": domicilio.colonia if domicilio else "",
            "delegacionMunicipio": domicilio.ciudad if domicilio else "",
            "CP": domicilio.codigo_postal if domicilio else "",
            "direccion": domicilio.direccion if domicilio else "",
            "tipo_domicilio": domicilio.tipo if domicilio else "personal"
        }
    }
    """ 
    payload = {
        "primerNombre": "JUAN PRUEBA SIETE",
        "apellidoPaterno": "PRUEBA",
        "apellidoMaterno": "SIETE",
        "fechaNacimiento": "1965-08-09",
        "RFC": "PUSJ800107H2O",
        "nacionalidad": "MX",
        "domicilio": {
            "direccion": "INSURGENTES SUR 1001",
            "coloniaPoblacion": "INSURGENTES SUR",
            "delegacionMunicipio": "CIUDAD DE MEXICO",
            "ciudad": "CIUDAD DE MEXICO",
            "estado": "CDMX",
            "CP": "11230"
        }
    }
    
    current_app.logger.info(f"Payload enviado al historial crediticio: {payload}")

    url = "https://services.circulodecredito.com.mx/sandbox/v1/rcficoscore"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": "V1SGTznV4THR8Z0vSqyW3JIgWNnSY5Zv",
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        return jsonify({
            "datos_usados": payload,
            "resultado": response.json()
        }), 200
    else:
        return jsonify({
            "datos_usados": payload,
            "error": "Error obteniendo historial crediticio",
            "detalle": response.text
        }), response.status_code
    
@users_bp.post("/agregar-domicilio")
def agregar_domicilio():
    data = request.get_json() or {}

    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id es requerido"}), 400
    
    existente = Domicilio.query.filter_by(usuario_id=user_id).first()
    if existente:
        return jsonify({"error": "Ya existe un domicilio registrado para este usuario"}), 400
    
    direccion = data.get("direccion")
    colonia = data.get("colonia")
    ciudad = data.get("ciudad")
    estado = data.get("estado")
    codigo_postal = data.get("codigo_postal")
    tipo = data.get("tipo_domicilio", "personal")

    # Validar campos requeridos
    if not direccion or not colonia or not ciudad or not estado or not codigo_postal:
        return jsonify({"error": "Todos los campos de dirección son obligatorios"}), 400

    # Crear nueva instancia de domicilio (asumiendo que tienes modelo Domicilio)
    nuevo_domicilio = Domicilio(
        usuario_id=user_id,
        direccion=direccion,
        colonia=colonia,
        ciudad=ciudad,
        estado=estado,
        codigo_postal=codigo_postal,
        tipo=tipo
    )

    try:
        db.session.add(nuevo_domicilio)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al agregar domicilio: {e}")
        return jsonify({"error": "No se pudo agregar el domicilio"}), 500

    return jsonify({
        "msg": "Domicilio agregado correctamente",
        "domicilio": nuevo_domicilio.serialize()  # Asegúrate que serialize() esté definido en Domicilio
    }), 201
    
@users_bp.get("/saldo/<codigo>")
def obtener_saldo(codigo):
    # 1. Buscar usuario por su código único (ej. MP-UR6279)
    usuario = Usuario.query.filter_by(codigo=codigo).first()

    if not usuario:
        return jsonify({"success": False, "message": "Usuario no encontrado"}), 404

    # 2. Buscar contratos por cliente_id
    contratos = ContratoCompraVenta.query.filter_by(cliente_id=usuario.id).all()

    if not contratos:
        return jsonify({
            "success": True,
            "codigo": usuario.codigo,     # ← agregado
            "saldo_total": 0,
            "message": "El cliente no tiene contratos"
        }), 200

    # 3. Calcular saldo de todos los contratos
    saldos = [
        {
            "contrato_id": c.id,
            "saldo_pendiente": c.saldo_pendiente,
            "precio_total": float(c.precio_total)
        }
        for c in contratos
    ]

    saldo_total = sum(c["saldo_pendiente"] for c in saldos)

    return jsonify({
        "success": True,
        "cliente_id": usuario.id,
        "codigo": usuario.codigo,   # ← agregado
        "saldos": saldos,
        "saldo_total": saldo_total
    }), 200
    
@users_bp.get("/buscar")
def buscar_cliente():
    codigo = request.args.get("codigo")
    telefono = request.args.get("telefono")

    query = Usuario.query
    if codigo:
        query = query.filter_by(codigo=codigo)
    elif telefono:
        query = query.filter_by(numero_telefonico=telefono)
    else:
        return jsonify({"message": "Debes enviar un código o teléfono"}), 400

    cliente = query.first()
    if not cliente:
        return jsonify({"message": "Cliente no encontrado"}), 404

    return jsonify(cliente.serialize()), 200