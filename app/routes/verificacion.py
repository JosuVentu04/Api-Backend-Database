from flask import Blueprint, request, jsonify
import requests
import hmac
import hashlib

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
    url = f"https://stationapi.veriff.com/v1/sessions/{session_id}/attempts"
    headers = {
        "Content-Type": "application/json",
        "X-AUTH-CLIENT": API_KEY,
        "X-HMAC-SIGNATURE": generate_x_hmac_signature(session_id, SHARED_SECRET)
    }
    response = requests.get(url, headers=headers)
    return jsonify(response.json())