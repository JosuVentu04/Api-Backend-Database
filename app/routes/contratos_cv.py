from flask import Blueprint, request, jsonify, send_from_directory
from app.models import ContratoCompraVenta, Usuario, PlanPago, db
from app.utils import calcular_plan_pago
from decimal import Decimal
from datetime import datetime, timedelta
import hashlib
import os

contratos_cv_bp = Blueprint('contratos_cv', __name__, url_prefix='/api/contratos/compra-venta')

# 📂 Carpeta donde se guardarán los contratos HTML
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
CONTRATOS_DIR = os.path.join(BASE_DIR, '../static/contratos')
os.makedirs(CONTRATOS_DIR, exist_ok=True)


# ------------------------------------------------------------
# 1️⃣ Crear contrato de compra-venta
# ------------------------------------------------------------
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
        monto_base_dec = Decimal(str(monto_base)) if monto_base else monto_total_dec
        pago_inicial_dec = Decimal(str(pago_inicial))

        # Validación: Pago inicial menor o igual a 50% de base
        if pago_inicial_dec < 0 or pago_inicial_dec > (monto_base_dec / 2):
            return jsonify({"error": "Pago inicial inválido"}), 400

        # Calcular cuotas
        resultado_plan = calcular_plan_pago(plan, monto_total_dec, pago_inicial_dec, monto_base_dec)
        ultima_cuota = resultado_plan["cuotas"][-1] if resultado_plan["cuotas"] else 0

        # Actualizar plan
        plan.ultima_cuota_semanal = ultima_cuota
        db.session.commit()

        # Crear contrato
        contrato = ContratoCompraVenta(
            cliente_id=cliente_id,
            precio_total=monto_total_dec,
            pago_inicial=pago_inicial_dec,
            plan_pago_id=plan.id,
            pago_semanal=Decimal(str(resultado_plan["cuota_semanal"])),
            ultimo_pago_semanal=Decimal(str(ultima_cuota)),
            num_pagos_semanales=plan.duracion_semanas,
            proximo_pago_fecha=datetime.utcnow() + timedelta(weeks=1),
            estado_contrato="PENDIENTE",
            saldo_pendiente=monto_total_dec   # 🔥 AGREGADO
        )

        db.session.add(contrato)
        db.session.commit()

        return jsonify({
            "mensaje": "Contrato de compra-venta creado correctamente",
            "contrato": contrato.serialize(),
            "plan_actualizado": {
                "id": plan.id,
                "nombre_plan": plan.nombre_plan,
                "ultima_cuota_semanal": int(plan.ultima_cuota_semanal)
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        print("❌ Error al crear contrato:", str(e))
        return jsonify({"error": str(e)}), 500


# ------------------------------------------------------------
# 2️⃣ Obtener todos los contratos de compra-venta
# ------------------------------------------------------------
@contratos_cv_bp.route('/todos', methods=['GET'])
def obtener_todos_compra_venta():
    contratos = ContratoCompraVenta.query.all()
    return jsonify({"contratos": [c.serialize() for c in contratos]}), 200


# ------------------------------------------------------------
# 3️⃣ Obtener contrato por ID
# ------------------------------------------------------------
@contratos_cv_bp.route('/<int:contrato_id>', methods=['GET'])
def obtener_compra_venta_por_id(contrato_id):
    contrato = ContratoCompraVenta.query.get(contrato_id)
    if not contrato:
        return jsonify({"error": "Contrato no encontrado"}), 404
    return jsonify({"contrato": contrato.serialize()}), 200


# ------------------------------------------------------------
# 4️⃣ Firmar contrato de compra-venta (con hash + guardado HTML)
# ------------------------------------------------------------
@contratos_cv_bp.route('/firmar-contrato', methods=['POST'])
def firmar_contrato_compra_venta():
    data = request.get_json()
    contrato_id = data.get("contrato_id")
    contrato_html = data.get("contrato_html")
    hash_contrato = data.get("hash_contrato")
    empleado_id = data.get("empleado_id")

    if not all([contrato_id, contrato_html, hash_contrato]):
        return jsonify({"error": "Faltan datos para firmar el contrato"}), 400

    # 🔒 Validar integridad del contrato (hash)
    hash_servidor = hashlib.sha256(contrato_html.encode('utf-8')).hexdigest()
    if hash_servidor != hash_contrato:
        return jsonify({"success": False, "message": "El hash no coincide. El contrato fue alterado."}), 400

    # 🧾 Guardar contrato HTML en carpeta
    ruta_archivo = os.path.join(CONTRATOS_DIR, f'contrato_compra_venta_{contrato_id}.html')
    with open(ruta_archivo, 'w', encoding='utf-8') as f:
        f.write(contrato_html)

    contrato_url = f"{request.host_url}static/contratos/contrato_compra_venta_{contrato_id}.html"

    contrato = ContratoCompraVenta.query.get(contrato_id)
    if not contrato:
        return jsonify({'error': 'Contrato no encontrado'}), 404

    contrato.fecha_firma = datetime.utcnow()
    contrato.empleado_id = empleado_id
    contrato.estado_contrato = "FIRMADO"
    contrato.hash_contrato = hash_contrato
    contrato.contrato_html = contrato_html
    contrato.contrato_url = contrato_url

    db.session.commit()

    return jsonify({
        'success': True,
        'contrato': contrato.serialize(),
        'url_html': contrato_url
    }), 200


# ------------------------------------------------------------
# 5️⃣ Listar archivos HTML generados
# ------------------------------------------------------------
@contratos_cv_bp.route('/archivos', methods=['GET'])
def listar_archivos_contratos_cv():
    if not os.path.exists(CONTRATOS_DIR):
        return {"error": "La carpeta de contratos no existe"}, 404

    archivos = [f for f in os.listdir(CONTRATOS_DIR) if f.startswith('contrato_compra_venta_')]
    return {"contratos_disponibles": archivos}


# ------------------------------------------------------------
# 6️⃣ Abrir contrato HTML por ID
# ------------------------------------------------------------
@contratos_cv_bp.route('/archivos/<contrato_id>', methods=['GET'])
def abrir_contrato_compra_venta(contrato_id):
    archivo = f"contrato_compra_venta_{contrato_id}.html"
    ruta_archivo = os.path.join(CONTRATOS_DIR, archivo)

    if os.path.exists(ruta_archivo):
        return send_from_directory(CONTRATOS_DIR, archivo)

    # Si no existe el archivo
    archivos = [f for f in os.listdir(CONTRATOS_DIR) if f.endswith('.html')]
    return jsonify({
        "error": f"Contrato {contrato_id} no encontrado",
        "contratos_disponibles": archivos
    }), 404