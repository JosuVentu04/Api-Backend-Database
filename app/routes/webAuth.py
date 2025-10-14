from flask import Blueprint, jsonify, request
from webauthn import (
    generate_registration_options,
    generate_authentication_options,
    verify_registration_response,
    verify_authentication_response,
    options_to_json
)

webauthn_bp = Blueprint("webauthn", __name__, url_prefix="/api/webauthn")

# En memoria (ejemplo). En producción guarda esto en tu BD.
users = {}
credentials = {}


@webauthn_bp.route("/register-options", methods=["GET"])
def get_registration_options():
    # Este flujo es cuando un usuario se registra por primera vez
    options = generate_registration_options(
        rp_id="localhost",            # tu dominio en producción
        rp_name="MarcelPay",
        user_id=b"user123",           # ID único de usuario en bytes
        user_name="usuario@example.com"
    )
    return jsonify(options_to_json(options))


@webauthn_bp.route("/options", methods=["GET"])
def get_authentication_options():
    # Este es el endpoint que llamas desde React
    options = generate_authentication_options(
        rp_id="localhost"
    )
    return jsonify(options_to_json(options))


@webauthn_bp.route("/verify", methods=["POST"])
def verify_authentication():
    data = request.get_json()
    try:
        verification = verify_authentication_response(
            credential=data,
            expected_rp_id="localhost",
            expected_origin="http://localhost:3000",  # tu frontend
            expected_challenge=None,  # aquí deberías validar contra el challenge guardado
        )
        return jsonify({"success": verification.verified})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400