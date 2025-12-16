from flask import Blueprint, request, jsonify, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta, date, time
from werkzeug.security import check_password_hash
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from numbers import Number


from app import db
from app.models import Pago, ContratoCompraVenta, EstadoDeuda, CorteCaja, Empleado, EstadoCorte, RolesEmpleado


pagos_bp = Blueprint('pagos_bp', __name__, url_prefix='/pagos')

CAMPOS_COMPARABLES = {
    "efectivo",
    "tarjeta",
    "transferencia",
    "total",
    "transacciones_tarjeta"
}

def validar_corte_editable(corte):
    if corte.estado != EstadoCorte.PENDIENTE:
        abort(409, description="El corte ya fue cerrado y no puede modificarse")

@pagos_bp.post('/registrar')
@jwt_required()
def registrar_pago():
    user_id = get_jwt_identity()
    data = request.get_json()

    contrato_id = data.get('contrato_id')
    monto = data.get('monto')
    metodo = data.get('metodo')
    sucursal_id = data.get('sucursal_id')

    if not contrato_id or monto is None:
        return {'success': False, 'message': 'Faltan datos obligatorios'}, 400
    contrato = ContratoCompraVenta.query.get(contrato_id)
    if not contrato:
        return {'success': False, 'message': 'Contrato no encontrado'}, 404
    pago_semanal = float(contrato.pago_semanal)
    ultimo_pago = float(contrato.ultimo_pago_semanal)
    saldo_pendiente = float(contrato.saldo_pendiente)
    monto = float(monto)

    # ✔ Si paga el total
    if monto == saldo_pendiente:
        pagos_cubiertos = contrato.num_pagos_semanales
    else:
        if monto < pago_semanal:
            return {
                'success': False,
                'message': f"El monto mínimo es {pago_semanal}"
            }, 400
        if monto % pago_semanal != 0 and monto != ultimo_pago:
            return {
                'success': False,
                'message': 'El monto debe ser múltiplo del pago semanal o igual al último pago.'
            }, 400
        pagos_cubiertos = int(monto // pago_semanal)
    # 🟩 Registrar el pago CON FECHA DE MÉXICO
    pago = Pago(
        sucursal_id=sucursal_id,
        contrato_id=contrato.id,
        empleado_id=user_id,
        monto=monto,
        metodo=metodo,
        fecha=datetime.now(ZoneInfo('America/Mexico_City'))
    )

    db.session.add(pago)

    # Actualizar saldo
    contrato.saldo_pendiente = Decimal(str(saldo_pendiente - monto))
    if contrato.saldo_pendiente < 0:
        contrato.saldo_pendiente = Decimal('0')
    # Actualizar semanas
    if monto == saldo_pendiente or monto == ultimo_pago:
        contrato.num_pagos_semanales = 0
    else:
        contrato.num_pagos_semanales -= pagos_cubiertos
        if contrato.num_pagos_semanales < 0:
            contrato.num_pagos_semanales = 0
    # Actualizar fecha de próximo pago → también con horario de México
    hoy = datetime.now(ZoneInfo('America/Mexico_City'))
    semanas_por_sumar = pagos_cubiertos if pagos_cubiertos > 0 else 1

    if contrato.proximo_pago_fecha is None:
        contrato.proximo_pago_fecha = hoy
    contrato.proximo_pago_fecha += timedelta(days=7 * semanas_por_sumar)

    # Si ya terminó
    if contrato.saldo_pendiente <= 0 or contrato.num_pagos_semanales == 0:
        contrato.estado_deuda = EstadoDeuda.LIQUIDADO.value
    db.session.commit()

    # Historial actualizado
    historial = (
        Pago.query.filter_by(contrato_id=contrato.id).order_by(Pago.fecha.desc()).all()
    )

    return {
        'success': True,
        'message': 'Pago registrado.',
        'pagos_cubiertos': pagos_cubiertos,
        'saldo_pendiente': float(contrato.saldo_pendiente),
        'pagos_restantes': contrato.num_pagos_semanales,
        'proximo_pago': contrato.proximo_pago_fecha.isoformat(),
        'historial_pago': [p.to_dict() for p in historial]
    }, 200


@pagos_bp.get('/historial/<int:contrato_id>')
def historial_pagos(contrato_id):
    pagos = (
        Pago.query.filter_by(contrato_id=contrato_id).order_by(Pago.fecha.desc()).all()
    )

    return {'success': True, 'historial': [p.to_dict() for p in pagos]}, 200


@pagos_bp.get('/al-corte/<int:empleado_id>')
def pagos_al_corte(empleado_id):
    hoy = datetime.now(ZoneInfo('America/Mexico_City')).date()

    inicio = datetime.combine(
        hoy, datetime.min.time(), tzinfo=ZoneInfo('America/Mexico_City')
    )
    fin = datetime.combine(
        hoy, datetime.max.time(), tzinfo=ZoneInfo('America/Mexico_City')
    )

    pagos = (
        Pago.query.filter(
            Pago.empleado_id == empleado_id, Pago.fecha >= inicio, Pago.fecha <= fin
        )
        .order_by(Pago.fecha.desc())
        .all()
    )

    return {'success': True, 'pagos': [p.to_dict() for p in pagos]}, 200


@pagos_bp.post('/abrir/corte')
def abrir_corte():
    data = request.get_json()
    empleado_id = data.get('empleado_id')
    sucursal_id = data.get('sucursal_id')

    # O usuario_id si así está en tu DB

    hoy = date.today()

    inicio = datetime.combine(hoy, time.min)
    fin = datetime.combine(hoy, time.max)

    # Buscar si ya existe corte del día
    corte = CorteCaja.query.filter(
        CorteCaja.empleado_id == empleado_id,
        CorteCaja.sucursal_id == sucursal_id,
        CorteCaja.fecha_corte >= inicio,
        CorteCaja.fecha_corte <= fin
    ).first()

    # Obtener pagos del día
    pagos_hoy = Pago.query.filter(
        Pago.fecha >= inicio,
        Pago.fecha <= fin,
        Pago.sucursal_id == sucursal_id,
        Pago.empleado_id == empleado_id
    ).all()

    # Calcular totales y cantidades
    total_efectivo = sum(p.monto for p in pagos_hoy if p.metodo == 'EFECTIVO')
    total_tarjeta = sum(p.monto for p in pagos_hoy if p.metodo == 'TARJETA')
    total_transferencia = sum(p.monto for p in pagos_hoy if p.metodo == 'TRANSFERENCIA')

    trans_efectivo = len([p for p in pagos_hoy if p.metodo == 'EFECTIVO'])
    trans_tarjeta = len([p for p in pagos_hoy if p.metodo == 'TARJETA'])
    trans_transferencia = len([p for p in pagos_hoy if p.metodo == 'TRANSFERENCIA'])

    total_general = total_efectivo + total_tarjeta + total_transferencia

    # Si ya existe → actualizar
    if corte:
        corte.total_efectivo = total_efectivo
        corte.total_tarjeta = total_tarjeta
        corte.total_transferencia = total_transferencia
        corte.trans_efectivo = trans_efectivo
        corte.trans_tarjeta = trans_tarjeta
        corte.trans_transferencia = trans_transferencia
        corte.total_general = total_general
        corte.sucursal_id = sucursal_id

        db.session.commit()
        return {'success': True, 'corte': corte.to_dict()}, 200
    # Si no existe → crear nuevo
    nuevo_corte = CorteCaja(
        sucursal_id=sucursal_id,
        empleado_id=empleado_id,
        fecha_corte=hoy,
        total_efectivo=total_efectivo,
        total_tarjeta=total_tarjeta,
        total_transferencia=total_transferencia,
        trans_efectivo=trans_efectivo,
        trans_tarjeta=trans_tarjeta,
        trans_transferencia=trans_transferencia,
        total_general=total_general
    )

    db.session.add(nuevo_corte)
    db.session.commit()

    return {'success': True, 'corte': nuevo_corte.to_dict()}, 201


@pagos_bp.route('/corte-caja/comparar/<int:corte_id>', methods=['POST'])
def comparar_corte(corte_id):
    corte = CorteCaja.query.get(corte_id)
    if not corte:
        return jsonify({'error': 'Corte de caja no encontrado'}), 404
    
    validar_corte_editable(corte)

    # 🔵 LO QUE SE TIENE (BD)
    datos_actuales = {
        'efectivo': corte.total_efectivo,
        'tarjeta': corte.total_tarjeta,
        'transferencia': corte.total_transferencia,
        'total': corte.total_general,
        'transacciones_tarjeta': corte.trans_tarjeta,
        'observaciones': corte.observaciones
    }

    # 🟢 LO QUE EL EMPLEADO DICE QUE TIENE (FORMULARIO)
    datos_declarados = request.json or {}

    diferencias = {}

    for campo in CAMPOS_COMPARABLES:
        if campo not in datos_declarados:
            continue

        valor_declarado = datos_declarados[campo]
        valor_actual = datos_actuales.get(campo)

        if valor_actual != valor_declarado:
            diferencias[campo] = {
                "actual": valor_actual,
                "declarado": valor_declarado,
                "diferencia": (
                    valor_declarado - valor_actual
                    if isinstance(valor_declarado, Number)
                    and isinstance(valor_actual, Number)
                    else None
                )
            }

    return jsonify({
        'corte_id': corte_id,
        'actual': datos_actuales,
        'declarado': datos_declarados,
        'diferencias': diferencias,
        'observaciones': datos_declarados.get('observaciones')
    })

@pagos_bp.route('/corte-caja/confirmar-empleado/<int:corte_id>', methods=['POST'])
def confirmar_corte_empleado(corte_id):
    corte = CorteCaja.query.get_or_404(corte_id)
    
    validar_corte_editable(corte)
    
    data = request.json or {}

    correo = data.get('correo')
    password = data.get('password')

    if not correo or not password:
        return jsonify({'error': 'Correo y contraseña requeridos'}), 400

    empleado = Empleado.query.filter_by(correo=correo).first()
    if not empleado or not empleado.check_password(password):
        return jsonify({'error': 'Credenciales inválidas'}), 401

    if empleado.id != corte.empleado_id:
        return jsonify({'error': 'Este empleado no pertenece al corte'}), 403

    if corte.confirmado_empleado:
        return jsonify({'error': 'El corte ya fue confirmado'}), 400

    corte.real_efectivo = data.get('efectivo')
    corte.real_tarjeta = data.get('tarjeta')
    corte.real_transferencia = data.get('transferencia')

    corte.dif_efectivo = corte.real_efectivo - corte.total_efectivo
    corte.dif_tarjeta = corte.real_tarjeta - corte.total_tarjeta
    corte.dif_transferencia = corte.real_transferencia - corte.total_transferencia

    corte.observaciones = data.get('observaciones')
    corte.confirmado_empleado = True
    corte.fecha_confirmacion_empleado = datetime.utcnow()
    corte.estado = EstadoCorte.DECLARADO

    db.session.commit()

    return jsonify({
        "msg": "Corte confirmado por el empleado",
        "estado": corte.estado.value
    })
    
@pagos_bp.route('/corte-caja/cerrar/<int:corte_id>', methods=['POST'])
def cerrar_corte(corte_id):
    corte = CorteCaja.query.get_or_404(corte_id)

    empleado_id = request.json.get('empleado_id')
    if not empleado_id:
        return jsonify({'error': 'empleado_id requerido'}), 400

    empleado = Empleado.query.get_or_404(empleado_id)

    if empleado.rol not in [RolesEmpleado.GERENTE, RolesEmpleado.ADMIN]:
        return jsonify({'error': 'No autorizado'}), 403

    if not corte.confirmado_empleado:
        return jsonify({'error': 'El empleado no ha confirmado el corte'}), 400
    
    if empleado.id == corte.empleado_id:
        return jsonify({"error": "No puedes cerrar tu propio corte de caja"}), 403
    

    dif_total = (
        corte.dif_efectivo +
        corte.dif_tarjeta +
        corte.dif_transferencia
    )

    if dif_total == 0:
        corte.estado = EstadoCorte.COMPLETO
    elif dif_total < 0:
        corte.estado = EstadoCorte.FALTANTE
    else:
        corte.estado = EstadoCorte.SOBRANTE

    corte.confirmado_admin = True
    corte.fecha_cierre = datetime.utcnow()
    corte.cerrado_por_admin_id = empleado.id

    db.session.commit()

    return jsonify({
        "msg": "Corte cerrado correctamente",
        "estado": corte.estado.value,
        "diferencia_total": float(dif_total)
    })
