from flask import Blueprint, request, jsonify
from app.models import ConsultasVerificacion, db, TipoIdentificacion
import requests
import hmac
import hashlib
import json

veriff_bp = Blueprint('veriff', __name__, url_prefix='/api/veriff')

API_KEY = "1953b936-62e0-4450-9abf-ccbf998ef1bb"
SHARED_SECRET = "e1d54698-b461-419a-9435-ff1c7e3e9df4"

def generate_x_hmac_signature(payload: dict, secret: str) -> str:
    """
    Genera la firma HMAC-SHA256 a partir del JSON canonizado.
    """
    body = json.dumps(payload, separators=(',', ':'))
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()

@veriff_bp.route('/create-session', methods=['POST'])
def crear_sesion_veriff():
    user_id = request.json.get('userId')
    customer_name = request.json.get('customerName')
    customer_lastname = request.json.get('customerLastName')
    
    url = "https://stationapi.veriff.com/v1/sessions/"
    headers = {
        "Content-Type": "application/json",
        "X-AUTH-CLIENT": API_KEY
    }
    payload = {
        "verification": {
            "vendorData": user_id,
            "person": {
                "firstName": customer_name,
                "lastName": customer_lastname
            },
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    return jsonify(response.json()), response.status_code

@veriff_bp.route('/status/<session_id>', methods=['GET'])
def obtener_estado_veriff(session_id):
    url = f"https://stationapi.veriff.com/v1/sessions/{session_id}/decision"
    signature = hmac.new(
        SHARED_SECRET.encode(),
        session_id.encode(),
        hashlib.sha256
    ).hexdigest()

    print("Signature usada:", signature)
    headers = {
        "Content-Type": "application/json",
        "X-AUTH-CLIENT": API_KEY,
        "X-HMAC-SIGNATURE": signature
    }
    response = requests.get(url, headers=headers)
    return jsonify(response.json()), response.status_code

def subir_media(session_id, image_base64, media_type):
    url = f"https://stationapi.veriff.com/v1/sessions/{session_id}/media"
    payload = {
        "image": {
            "content": image_base64,
            "context": media_type
        }
    }
    body = json.dumps(payload, separators=(',', ':'))
    signature = hmac.new(SHARED_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-AUTH-CLIENT": API_KEY,
        "X-HMAC-SIGNATURE": signature
    }
    response = requests.post(url, data=body, headers=headers)
    print("Clave Secreta:", SHARED_SECRET)
    print("Payload enviado a Veriff:", json.dumps(payload, separators=(',', ':')))
    print("Headers enviados:", headers)
    print("Respuesta de Veriff:", response.status_code, response.text)
    print("Respuesta completa de Veriff:", response.json())
    print(session_id, media_type)
    return response

@veriff_bp.route('/upload/front/<session_id>', methods=['POST'])
def subir_documento_frontal(session_id):
    image_base64 = request.json.get('image')
    response = subir_media(session_id, image_base64, "document-front")
    return jsonify(response.json()), response.status_code

@veriff_bp.route('/upload/back/<session_id>', methods=['POST'])
def subir_documento_trasero(session_id):
    image_base64 = request.json.get('image')
    response = subir_media(session_id, image_base64, "document-back")
    return jsonify(response.json()), response.status_code

@veriff_bp.route('/upload/selfie/<session_id>', methods=['POST'])
def subir_selfie(session_id):
    image_base64 = request.json.get('image')
    response = subir_media(session_id, image_base64, "face")
    return jsonify(response.json()), response.status_code

@veriff_bp.route('/submit-session/<session_id>', methods=['PATCH'])
def submit_session(session_id):
    url = f"https://stationapi.veriff.com/v1/sessions/{session_id}"
    payload = {
        "verification": {
            "status": "submitted"
        }
    }
    signature = generate_x_hmac_signature(payload, SHARED_SECRET)
    headers = {
        "Content-Type": "application/json",
        "X-AUTH-CLIENT": API_KEY,
        "X-HMAC-SIGNATURE": signature
    }
    try:
        body = json.dumps(payload, separators=(',', ':'))
        signature = generate_x_hmac_signature(payload, SHARED_SECRET)
        headers = {
            "Content-Type": "application/json",
            "X-AUTH-CLIENT": API_KEY,
            "X-HMAC-SIGNATURE": signature
        }
        response = requests.patch(url, data=body, headers=headers)
        response.raise_for_status()
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        return jsonify({"error": "No se pudo enviar la sesión a Veriff", "detalle": str(e)}), 500

@veriff_bp.route('/guardar-consulta', methods=['POST'])
def guardar_consulta():
    data = request.get_json()
    nueva_consulta = ConsultasVerificacion(
        primer_nombre=data['primer_nombre'],
        apellido_paterno=data['apellido_paterno'],
        empleado_id=int(data['empleado_id']),
        usuario_id=int(data['usuario_id']),
        session_id=data.get('session_id'),
        motivo_consulta=data.get('motivo_consulta'),
        resultado_consulta=data.get('resultado_consulta'),
    )
    db.session.add(nueva_consulta)
    db.session.commit()
    return jsonify({"status": "success", "id": nueva_consulta.id})

@veriff_bp.route('/historial-consultas', methods=['GET'])
def historial_consultas():
    consultas = ConsultasVerificacion.query.all()
    resultado = [consulta.serialize() for consulta in consultas]
    return jsonify(resultado)