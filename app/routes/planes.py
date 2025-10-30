from flask import Blueprint, request, jsonify
from app import db
from app.models import PlanPago, calcular_plan_pago
from app.utils import calcular_plan_pago
from decimal import Decimal

planes_bp = Blueprint('planes_bp', __name__, url_prefix='/api/planes')

@planes_bp.route('/crear', methods=['POST'])
def crear_plan():
    data = request.get_json()

    # ✅ Validaciones básicas
    nombre = data.get('nombre_plan')
    duracion = data.get('duracion_semanas')
    interes = data.get('tasa_interes', 0)
    pago_inicial = data.get('pago_inicial', 0)

    if not nombre or not duracion:
        return jsonify({'error': 'Nombre del plan y duración son obligatorios'}), 400
    if duracion <= 0:
        return jsonify({'error': 'La duración debe ser mayor a 0'}), 400
    if interes < 0:
        return jsonify({'error': 'La tasa de interés no puede ser negativa'}), 400
    if pago_inicial < 0:
        return jsonify({'error': 'El pago inicial no puede ser negativo'}), 400

    # ✅ Crear el plan
    plan = PlanPago(
        nombre_plan=nombre,
        duracion_semanas=duracion,
        tasa_interes=interes,
        pago_inicial=pago_inicial
    )
    db.session.add(plan)
    db.session.commit()

    # ✅ Respuesta
    return jsonify({
        'id': plan.id,
        'nombre_plan': plan.nombre_plan,
        'duracion_semanas': plan.duracion_semanas,
        'tasa_interes': plan.tasa_interes,
        'pago_inicial': plan.pago_inicial
    }), 201
    
@planes_bp.route('/calcular_plan_pago', methods=['POST'])
def calcular_plan_pago_endpoint():
    data = request.get_json()
    print("Datos recibidos:", data)

    plan_id = data.get('plan_id')
    monto_total = data.get('monto_total')
    pago_inicial = data.get('pago_inicial')  # opcional

    print(f"plan_id: {plan_id}, monto_total: {monto_total}, pago_inicial: {pago_inicial}")

    if plan_id is None or monto_total is None:
        print("Error: plan_id y monto_total son requeridos")
        return jsonify({'error': 'plan_id y monto_total son requeridos'}), 400

    plan = PlanPago.query.get(plan_id)
    if not plan:
        print("Error: Plan no encontrado")
        return jsonify({'error': 'Plan no encontrado'}), 404

    print("Plan encontrado:", plan)

    try:
        # Convertir a Decimal para evitar errores de tipos
        monto_total_decimal = Decimal(str(monto_total))
        pago_inicial_decimal = (
            Decimal(str(pago_inicial)) if pago_inicial is not None else None
        )

        print("Monto total como Decimal:", monto_total_decimal)
        print("Pago inicial como Decimal:", pago_inicial_decimal)

        resultado = calcular_plan_pago(plan, monto_total_decimal, pago_inicial_decimal)

        print("Resultado calculado:", resultado)
        return jsonify(resultado)
    except Exception as e:
        print("Ocurrió un error:", str(e))
        return jsonify({'error': str(e)}), 500