from flask import Blueprint, request, jsonify
from app.models import consultas_verificacion, db, consultas_verificacion, TipoIdentificacion
import requests
import hmac
import hashlib
import base64

veriff_bp = Blueprint('veriff', __name__, url_prefix='/api/veriff')

API_KEY = "1953b936-62e0-4450-9abf-ccbf998ef1bb"
SHARED_SECRET = "e1d54698-b461-419a-9435-ff1c7e3e9df4"

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
    return jsonify(response.json())



def generate_x_hmac_signature(session_id, secret):
    # Devuelve solo el hash en hexadecimal, sin 'sha256='
    return hmac.new(
        secret.encode(),
        session_id.encode(),
        hashlib.sha256
    ).hexdigest()


@veriff_bp.route('/status/<session_id>', methods=['GET'])
def obtener_estado_veriff(session_id):
    url = f"https://stationapi.veriff.com/v1/sessions/{session_id}/decision"
    headers = {
        "Content-Type": "application/json",
        "X-AUTH-CLIENT": API_KEY,
        "X-HMAC-SIGNATURE": generate_x_hmac_signature(session_id, SHARED_SECRET)
    }
    response = requests.get(url, headers=headers)
    return jsonify(response.json())

@veriff_bp.route('/upload/front/<session_id>', methods=['POST'])
def subir_documento_frontal(session_id):
    """
    Sube la imagen frontal del documento a Veriff
    """
    image_base64 = request.json.get('image')
    url = f"https://stationapi.veriff.com/v1/sessions/{session_id}/media"

    headers = {
        "Content-Type": "application/json",
        "X-AUTH-CLIENT": API_KEY,
        "X-HMAC-SIGNATURE": generate_x_hmac_signature(session_id, SHARED_SECRET)
    }

    payload = {
        "media": {
            "content": image_base64,
            "type": "document-front"
        }
    }

    response = requests.post(url, json=payload, headers=headers)
    return jsonify(response.json())


@veriff_bp.route('/upload/back/<session_id>', methods=['POST'])
def subir_documento_trasero(session_id):
    """
    Sube la imagen trasera del documento a Veriff
    """
    image_base64 = request.json.get('image')
    url = f"https://stationapi.veriff.com/v1/sessions/{session_id}/media"

    headers = {
        "Content-Type": "application/json",
        "X-AUTH-CLIENT": API_KEY,
        "X-HMAC-SIGNATURE": generate_x_hmac_signature(session_id, SHARED_SECRET)
    }

    payload = {
        "media": {
            "content": image_base64,
            "type": "document-back"
        }
    }

    response = requests.post(url, json=payload, headers=headers)
    return jsonify(response.json())


@veriff_bp.route('/upload/selfie/<session_id>', methods=['POST'])
def subir_selfie(session_id):
    """
    Sube la selfie del usuario a Veriff
    """
    image_base64 = request.json.get('image')
    url = f"https://stationapi.veriff.com/v1/sessions/{session_id}/media"

    headers = {
        "Content-Type": "application/json",
        "X-AUTH-CLIENT": API_KEY,
        "X-HMAC-SIGNATURE": generate_x_hmac_signature(session_id, SHARED_SECRET)
    }

    payload = {
        "media": {
            "content": image_base64,
            "type": "selfie"  # también puede usarse "face-reference"
        }
    }

    response = requests.post(url, json=payload, headers=headers)
    return jsonify(response.json())

@veriff_bp.route('/submit-session/<session_id>', methods=['PATCH'])
def submit_session(session_id):
    url = f"https://stationapi.veriff.com/v1/sessions/{session_id}"
    headers = {
        "Content-Type": "application/json",
        "X-AUTH-CLIENT": API_KEY,
        "X-HMAC-SIGNATURE": generate_x_hmac_signature(session_id, SHARED_SECRET)
    }
    payload = {
        "verification": {
            "status": "submitted"
        }
    }
    try:
        response = requests.patch(url, json=payload, headers=headers)
        response.raise_for_status()
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        return jsonify({"error": "No se pudo enviar la sesión a Veriff", "detalle": str(e)}), 500

@veriff_bp.route('/guardar-consulta', methods=['POST'])
def guardar_consulta():
    data = request.get_json()
    nueva_consulta = consultas_verificacion(
        nombre=data['nombre'],
        apellido=data['apellido'],
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
    consultas = consultas_verificacion.query.all()
    resultado = [consulta.serialize() for consulta in consultas]
    return jsonify(resultado)