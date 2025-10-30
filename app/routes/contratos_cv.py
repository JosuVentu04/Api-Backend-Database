from flask import Blueprint, request, jsonify
from app.models import ContratoCompraVenta, Usuario, PlanPago, db
from app.utils import calcular_plan_pago
from decimal import Decimal
from datetime import datetime, timedelta

contratos_cv_bp = Blueprint('contratos_cv', __name__, url_prefix='/api/contratos/compra-venta')


# 1️⃣ Crear contrato de compra-venta (ya lo tienes, solo lo ajustamos)
@contratos_cv_bp.route('/crear', methods=['POST'])
def crear_contrato_compra_venta():
    data = request.get_json()
    cliente_id = data.get("cliente_id")
    plan_id = data.get("plan_id")
    monto_base = data.get("monto_base")
    monto_total = data.get("monto_total")
    pago_inicial = data.get("pago_inicial", 0)

    if not all([cliente_id, plan_id, monto_total]):
        return jsonify({"error": "cliente_id, plan_id y monto_total son requeridos"}), 400

    usuario = Usuario.query.get(cliente_id)
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404

    plan = PlanPago.query.get(plan_id)
    if not plan:
        return jsonify({"error": "Plan no encontrado"}), 404

    try:
        monto_total_dec = Decimal(str(monto_total))
        monto_base_dec = Decimal(str(monto_base)) if monto_base else Decimal("0")
        pago_inicial_dec = Decimal(str(pago_inicial))

        if pago_inicial_dec < 0 or pago_inicial_dec > (monto_base_dec / 2):
            return jsonify({"error": "Pago inicial inválido"}), 400

        resultado_plan = calcular_plan_pago(plan, monto_total_dec, pago_inicial_dec, monto_base_dec)

        contrato = ContratoCompraVenta(
            cliente_id=cliente_id,
            precio_total=monto_total_dec,
            pago_inicial=pago_inicial_dec,
            plan_pago_id=plan.id,
            pago_semanal=Decimal(str(resultado_plan["cuota_semanal"])),
            num_pagos_semanales=plan.duracion_semanas,
            proximo_pago_fecha=datetime.utcnow() + timedelta(weeks=1)
        )

        db.session.add(contrato)
        db.session.commit()

        return jsonify({
            "mensaje": "Contrato de compra-venta creado correctamente",
            "contrato": {
                "id": contrato.id,
                "cliente_id": contrato.cliente_id,
                "precio_total": str(contrato.precio_total),
                "pago_inicial": str(contrato.pago_inicial),
                "pago_semanal": str(contrato.pago_semanal),
                "num_pagos_semanales": contrato.num_pagos_semanales,
                "proximo_pago_fecha": contrato.proximo_pago_fecha.isoformat()
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# 2️⃣ Obtener todos los contratos de compra-venta
@contratos_cv_bp.route('/todos', methods=['GET'])
def obtener_todos_compra_venta():
    contratos = ContratoCompraVenta.query.all()
    return jsonify({"contratos": [c.serialize() for c in contratos]}), 200


# 3️⃣ Obtener contrato de compra-venta por ID
@contratos_cv_bp.route('/<int:contrato_id>', methods=['GET'])
def obtener_compra_venta_por_id(contrato_id):
    contrato = ContratoCompraVenta.query.get(contrato_id)
    if not contrato:
        return jsonify({"error": "Contrato no encontrado"}), 404
    return jsonify({"contrato": contrato.serialize()}), 200


# 4️⃣ Firmar contrato de compra-venta
@contratos_cv_bp.route('/firmar', methods=['POST'])
def firmar_compra_venta():
    data = request.get_json()
    contrato_id = data.get("contrato_id")
    contrato_html = data.get("contrato_html")
    hash_contrato = data.get("hash_contrato")

    contrato = ContratoCompraVenta.query.get(contrato_id)
    if not contrato:
        return jsonify({"error": "Contrato no encontrado"}), 404

    contrato.fecha_firma = datetime.utcnow()
    contrato.contrato_html = contrato_html
    contrato.hash_contrato = hash_contrato

    db.session.commit()
    return jsonify({"success": True, "contrato": contrato.serialize()}), 200