from flask import Blueprint, request, jsonify, send_from_directory, abort, current_app
from app.models import ContratoConsultaBuro, EstadoContrato, db
from datetime import datetime
import os
import hashlib

# Blueprint
contratos_bp = Blueprint('contratos', __name__, url_prefix='/api/contratos')

# Carpeta donde se guardarán todos los contratos HTML
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
CONTRATOS_DIR = os.path.join(BASE_DIR, '../static/contratos')
os.makedirs(CONTRATOS_DIR, exist_ok=True)


# -----------------------------
# Crear contrato en base de datos
# -----------------------------
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
        nuevo_contrato = ContratoConsultaBuro(
            cliente_id=cliente_id,
            empleado_id=empleado_id,
            contrato_url=contrato_url,
            hash_contrato=hash_contrato,
            estado_contrato=EstadoContrato(estado_contrato),
            fecha_firma=None,
            contrato_html=None,
            nombre=data.get('nombre'),
            apellido=data.get('apellido'),
        )

        db.session.add(nuevo_contrato)
        db.session.commit()

        return jsonify({'success': True, 'contrato': nuevo_contrato.serialize()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error al crear contrato', 'message': str(e)}), 500


# -----------------------------
# Obtener todos los contratos
# -----------------------------
@contratos_bp.route('/todos', methods=['GET'])
def obtener_todos_contratos():
    contratos = ContratoConsultaBuro.query.all()
    return jsonify({'contratos': [c.serialize() for c in contratos]}), 200


# -----------------------------
# Obtener contrato por ID
# -----------------------------
@contratos_bp.route('/<int:contrato_id>', methods=['GET'])
def obtener_contrato_por_id(contrato_id):
    contrato = ContratoConsultaBuro.query.get(contrato_id)
    if not contrato:
        return jsonify({'error': 'Contrato no encontrado'}), 404
    return jsonify({'contrato': contrato.serialize()}), 200


# -----------------------------
# Firmar contrato y guardar HTML
# -----------------------------
@contratos_bp.route('/firmar-contrato', methods=['POST'])
def firmar_contrato():
    data = request.get_json()
    contrato_id = data.get('contrato_id')
    contrato_html = data.get('contrato_html')
    hash_contrato = data.get('hash_contrato')

    if not all([contrato_id, contrato_html, hash_contrato]):
        return jsonify({'error': 'Faltan datos para firmar el contrato'}), 400

    # Validar hash
    hash_servidor = hashlib.sha256(contrato_html.encode('utf-8')).hexdigest()
    if hash_servidor != hash_contrato:
        return jsonify({'success': False, 'message': 'El hash no coincide. El contrato fue alterado.'}), 400

    # Guardar archivo HTML
    ruta_archivo = os.path.join(CONTRATOS_DIR, f'contrato_{contrato_id}.html')
    with open(ruta_archivo, 'w', encoding='utf-8') as f:
        f.write(contrato_html)

    contrato_url = f"{request.host_url}static/contratos/contrato_{contrato_id}.html"

    contrato = ContratoConsultaBuro.query.get(contrato_id)
    if not contrato:
        return jsonify({'error': 'Contrato no encontrado'}), 404

    # Actualizar campos de firma
    contrato.fecha_firma = data.get('fecha_firma', datetime.utcnow())
    contrato.estado_contrato = EstadoContrato.FIRMADO.value
    contrato.contrato_html = contrato_html
    contrato.hash_contrato = hash_contrato
    contrato.contrato_url = contrato_url

    db.session.commit()

    return jsonify({'success': True, 'contrato': contrato.serialize(), 'url_html': contrato_url}), 200


# -----------------------------
# Listar archivos HTML en carpeta
# -----------------------------
@contratos_bp.route('/contratos', methods=['GET'])
def listar_contratos():
    if not os.path.exists(CONTRATOS_DIR):
        return {"error": "La carpeta de contratos no existe"}, 404

    contratos = [f for f in os.listdir(CONTRATOS_DIR) if f.endswith('.html')]
    return {"contratos_disponibles": contratos}


# -----------------------------
# Abrir un contrato por ID
# -----------------------------
@contratos_bp.route('/contratos/<contrato_id>', methods=['GET'])
def abrir_contrato(contrato_id):
    # Buscamos coincidencia exacta
    archivo = f"contrato_{contrato_id}.html"
    ruta_archivo = os.path.join(CONTRATOS_DIR, archivo)

    if os.path.exists(ruta_archivo):
        return send_from_directory(CONTRATOS_DIR, archivo)

    # Si no existe, buscamos por contenido dentro de los HTML
    encontrados = []
    for f in os.listdir(CONTRATOS_DIR):
        if f.endswith('.html'):
            with open(os.path.join(CONTRATOS_DIR, f), 'r', encoding='utf-8') as file:
                if contrato_id in file.read():
                    encontrados.append(f)

    if encontrados:
        # Devuelve el primero que coincida por contenido
        return send_from_directory(CONTRATOS_DIR, encontrados[0])

    # Si no hay coincidencias, devolvemos error con lista de archivos existentes
    contratos_existentes = [f for f in os.listdir(CONTRATOS_DIR) if f.endswith('.html')]
    return jsonify({
        "error": f"Contrato {contrato_id} no encontrado",
        "contratos_disponibles": contratos_existentes
    }), 404
