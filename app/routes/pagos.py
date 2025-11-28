from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from app import db
from app.models import Pago
from app.models import ContratoCompraVenta, EstadoDeuda

pagos_bp = Blueprint("pagos_bp", __name__, url_prefix="/pagos")



@pagos_bp.post("/registrar")
@jwt_required()
def registrar_pago():
    user_id = get_jwt_identity()
    data = request.get_json()

    contrato_id = data.get("contrato_id")
    monto = data.get("monto")
    metodo = data.get("metodo")

    if not contrato_id or monto is None:
        return {"success": False, "message": "Faltan datos obligatorios"}, 400

    contrato = ContratoCompraVenta.query.get(contrato_id)
    if not contrato:
        return {"success": False, "message": "Contrato no encontrado"}, 404

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
                "success": False,
                "message": f"El monto mínimo es {pago_semanal}"
            }, 400

        if monto % pago_semanal != 0 and monto != ultimo_pago:
            return {
                "success": False,
                "message": "El monto debe ser múltiplo del pago semanal o igual al último pago."
            }, 400

        pagos_cubiertos = int(monto // pago_semanal)

    # 🟩 Registrar el pago CON FECHA DE MÉXICO
    pago = Pago(
        contrato_id=contrato.id,
        empleado_id=user_id,
        monto=monto,
        metodo=metodo,
        fecha=datetime.now(ZoneInfo("America/Mexico_City"))
    )

    db.session.add(pago)

    # Actualizar saldo
    contrato.saldo_pendiente = Decimal(str(saldo_pendiente - monto))
    if contrato.saldo_pendiente < 0:
        contrato.saldo_pendiente = Decimal("0")

    # Actualizar semanas
    if monto == saldo_pendiente or monto == ultimo_pago:
        contrato.num_pagos_semanales = 0
    else:
        contrato.num_pagos_semanales -= pagos_cubiertos
        if contrato.num_pagos_semanales < 0:
            contrato.num_pagos_semanales = 0

    # Actualizar fecha de próximo pago → también con horario de México
    hoy = datetime.now(ZoneInfo("America/Mexico_City"))
    semanas_por_sumar = pagos_cubiertos if pagos_cubiertos > 0 else 1

    if contrato.proximo_pago_fecha is None:
        contrato.proximo_pago_fecha = hoy

    contrato.proximo_pago_fecha += timedelta(days=7 * semanas_por_sumar)

    # Si ya terminó
    if contrato.saldo_pendiente <= 0 or contrato.num_pagos_semanales == 0:
        contrato.estado_deuda = EstadoDeuda.LIQUIDADO.value

    db.session.commit()

    # Historial actualizado
    historial = Pago.query.filter_by(contrato_id=contrato.id).order_by(Pago.fecha.desc()).all()

    return {
        "success": True,
        "message": "Pago registrado.",
        "pagos_cubiertos": pagos_cubiertos,
        "saldo_pendiente": float(contrato.saldo_pendiente),
        "pagos_restantes": contrato.num_pagos_semanales,
        "proximo_pago": contrato.proximo_pago_fecha.isoformat(),
        "historial_pago": [p.to_dict() for p in historial]
    }, 200

@pagos_bp.get("/historial/<int:contrato_id>")
def historial_pagos(contrato_id):
    pagos = Pago.query.filter_by(contrato_id=contrato_id).order_by(Pago.fecha.desc()).all()

    return {
        "success": True,
        "historial": [p.to_dict() for p in pagos]
    }, 200