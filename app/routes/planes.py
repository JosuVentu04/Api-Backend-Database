from flask import Blueprint, request, jsonify
from app import db
from app.models import PlanPago
from app.utils import calcular_plan_pago
from decimal import Decimal

planes_bp = Blueprint('planes_bp', __name__, url_prefix='/api/planes')


@planes_bp.route('/calcular_y_actualizar', methods=['POST'])
def calcular_y_actualizar_plan():
    data = request.get_json()
    print("📥 Datos recibidos:", data)

    plan_id = data.get("plan_id")
    monto_total = data.get("monto_total")
    monto_base = data.get("monto_base")
    pago_inicial = data.get("pago_inicial")

    if not plan_id or monto_total is None:
        return jsonify({"error": "plan_id y monto_total son requeridos"}), 400

    # 🔍 Buscar plan existente
    plan = PlanPago.query.get(plan_id)
    if not plan:
        return jsonify({"error": "Plan no encontrado"}), 404

    try:
        # 💰 Convertir a Decimal
        monto_total_decimal = Decimal(str(monto_total))
        monto_base_decimal = Decimal(str(monto_base)) if monto_base else monto_total_decimal
        pago_inicial_decimal = Decimal(str(pago_inicial)) if pago_inicial is not None else Decimal(str(plan.pago_inicial))

        print(f"✅ Plan encontrado: {plan.nombre_plan}")
        print(f"💵 monto_total={monto_total_decimal}, pago_inicial={pago_inicial_decimal}, monto_base={monto_base_decimal}")

        # 🔢 Calcular cuotas
        resultado = calcular_plan_pago(plan, monto_total_decimal, pago_inicial_decimal, monto_base_decimal)
        print("📊 Resultado del cálculo:", resultado)

        # 🧾 Actualizar campo ultima_cuota_semanal
        ultima_cuota = resultado["cuotas"][-1] if resultado["cuotas"] else 0
        plan.ultima_cuota_semanal = ultima_cuota

        # 💾 Guardar cambios
        db.session.commit()

        # ✅ Respuesta
        return jsonify({
            "success": True,
            "plan_actualizado": {
                "id": plan.id,
                "nombre_plan": plan.nombre_plan,
                "duracion_semanas": plan.duracion_semanas,
                "tasa_interes": float(plan.tasa_interes),
                "pago_inicial": int(plan.pago_inicial),
                "ultima_cuota_semanal": int(plan.ultima_cuota_semanal)
            },
            "detalle_calculo": resultado
        }), 200

    except Exception as e:
        print("❌ Error:", str(e))
        return jsonify({"error": str(e)}), 500
    
