from flask import Blueprint, request, jsonify
from app.models import contrato_consulta_buro, EstadoContrato, db
from datetime import datetime

contratos_bp = Blueprint('contratos', __name__, url_prefix='/api/contratos')


@contratos_bp.route('/crear', methods=['POST'])
def crear_contrato():
    data = request.get_json()

    cliente_id = data.get('cliente_id')
    empleado_id = data.get('empleado_id')
    contrato_url = data.get('contrato_url')
    hash_contrato = data.get('hash_contrato')
    estado_contrato = data.get('estado_contrato', EstadoContrato.PENDIENTE.value)

    if not all([cliente_id, empleado_id, contrato_url, hash_contrato]):
        return jsonify({'error': 'Faltan campos obligatorios'}), 400

    try:
        nuevo_contrato = contrato_consulta_buro(
            cliente_id=cliente_id,
            empleado_id=empleado_id,
            contrato_url=contrato_url,
            hash_contrato=hash_contrato,
            estado_contrato=EstadoContrato(estado_contrato),
            fecha_firma=None,
            contrato_html=None,  # aún no hay contrato firmado
            nombre=data.get('nombre'),      # opcional
            apellido=data.get('apellido')   # opcional
        )

        db.session.add(nuevo_contrato)
        db.session.commit()

        return jsonify({'success': True, 'contrato': nuevo_contrato.serialize()}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error al crear contrato', 'message': str(e)}), 500


@contratos_bp.route('/todos', methods=['GET'])
def obtener_todos_contratos():
    contratos = contrato_consulta_buro.query.all()
    return jsonify({'contratos': [c.serialize() for c in contratos]}), 200


@contratos_bp.route('/<int:contrato_id>', methods=['GET'])
def obtener_contrato_por_id(contrato_id):
    contrato = contrato_consulta_buro.query.get(contrato_id)
    if not contrato:
        return jsonify({'error': 'Contrato no encontrado'}), 404
    return jsonify({'contrato': contrato.serialize()}), 200


@contratos_bp.route('/firmar-contrato', methods=['POST'])
def firmar_contrato():
    data = request.get_json()
    contrato_id = data.get('contrato_id')

    contrato = contrato_consulta_buro.query.get(contrato_id)
    if not contrato:
        return jsonify({'error': 'Contrato no encontrado'}), 404

    # Actualiza los campos de firma
    contrato.fecha_firma = data.get('fecha_firma', datetime.utcnow())
    contrato.estado_contrato = EstadoContrato.FIRMADO.value
    contrato.contrato_html = data.get('contrato_html')
    # Si lo deseas, actualiza hash_contrato si tienes el hash del HTML firmado
    contrato.hash_contrato = data.get('hash_contrato', contrato.hash_contrato)

    db.session.commit()
    return jsonify({'success': True, 'contrato': contrato.serialize()}), 200