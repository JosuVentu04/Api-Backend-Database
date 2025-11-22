from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal

from app import db
from app.models import Pago
from app.models import ContratoCompraVenta, EstadoDeuda

pagos_bp = Blueprint("pagos_bp", __name__, url_prefix="/pagos")


@pagos_bp.post("/registrar")
def registrar_pago():
    data = request.get_json()

    contrato_id = data.get("contrato_id")
    monto = data.get("monto")
    metodo = data.get("metodo")  # <-- tu frontend manda "metodo"

    if not contrato_id or monto is None:
        return {"success": False, "message": "Faltan datos obligatorios"}, 400

    contrato = ContratoCompraVenta.query.get(contrato_id)
    if not contrato:
        return {"success": False, "message": "Contrato no encontrado"}, 404

    pago_semanal = float(contrato.pago_semanal)
    ultimo_pago = float(contrato.ultimo_pago_semanal)
    saldo_pendiente = float(contrato.saldo_pendiente)
    monto = float(monto)

    # 🟦 VALIDACIÓN: Si paga el saldo total → permitir siempre
    if monto == saldo_pendiente:
        pagos_cubiertos = contrato.num_pagos_semanales

    else:
        # 🟥 VALIDACIÓN: El monto debe ser mayor o igual al pago semanal
        if monto < pago_semanal:
            return {
                "success": False,
                "message": f"El monto mínimo es {pago_semanal}"
            }, 400

        # 🟥 VALIDACIÓN: Debe ser múltiplo EXCEPTO si coincide con el último pago semanal
        if monto % pago_semanal != 0:
            if monto != ultimo_pago:
                return {
                    "success": False,
                    "message": "El monto debe ser múltiplo del pago semanal o igual al último pago."
                }, 400

        # Calcular semanas cubiertas
        pagos_cubiertos = int(monto // pago_semanal)

    # 🟩 Registrar el pago
    pago = Pago(
        contrato_id=contrato.id,
        monto=monto,
        metodo=metodo
    )
    db.session.add(pago)

    # 🟩 Restar saldo
    contrato.saldo_pendiente = Decimal(str(saldo_pendiente - monto))
    if contrato.saldo_pendiente < 0:
        contrato.saldo_pendiente = Decimal("0")

    # 🟩 Actualizar semanas restantes
    if monto == saldo_pendiente or monto == ultimo_pago:
        contrato.num_pagos_semanales = 0
    else:
        contrato.num_pagos_semanales -= pagos_cubiertos
        if contrato.num_pagos_semanales < 0:
            contrato.num_pagos_semanales = 0

    # 🟩 Actualizar próximo pago
    hoy = datetime.utcnow()
    semanas_por_sumar = pagos_cubiertos if pagos_cubiertos > 0 else 1

    if contrato.proximo_pago_fecha is None:
        contrato.proximo_pago_fecha = hoy

    contrato.proximo_pago_fecha += timedelta(days=7 * semanas_por_sumar)

    # 🟩 Si ya no hay saldo → COMPLETAR
    if contrato.saldo_pendiente <= 0 or contrato.num_pagos_semanales == 0:
        contrato.estado_deuda = EstadoDeuda.LIQUIDADO.value

    db.session.commit()

    return {
        "success": True,
        "message": "Pago registrado.",
        "pagos_cubiertos": pagos_cubiertos,
        "saldo_pendiente": float(contrato.saldo_pendiente),
        "pagos_restantes": contrato.num_pagos_semanales,
        "proximo_pago": contrato.proximo_pago_fecha.isoformat(),
    }, 200