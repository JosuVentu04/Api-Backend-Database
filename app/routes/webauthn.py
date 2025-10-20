from flask import Blueprint, request, jsonify, session
from flask_cors import CORS
from fido2.server import Fido2Server
from fido2.webauthn import PublicKeyCredentialRpEntity, PublicKeyCredentialUserEntity
from fido2.utils import websafe_encode

webauthn_bp = Blueprint('webauthn_bp', __name__, url_prefix='/api/webauthn')
CORS(webauthn_bp, supports_credentials=True)

# --- Configurar Relying Party ---
rp = PublicKeyCredentialRpEntity(id="localhost", name="MarcelPay Demo")
server = Fido2Server(rp)

# --- Base de datos en memoria ---
USERS = {}

# --- Registrar opciones ---

@webauthn_bp.route("/api/webauthn/register-options", methods=["GET"])
def register_options():
    user_id = "user-1"
    username = "demo_user"

    user = PublicKeyCredentialUserEntity(
        id=user_id.encode(), name=username, display_name=username
    )
    registration_data, state = server.register_begin(user, user_verification="preferred")
    session["state"] = state
    USERS[user_id] = {"credentials": []}

    # Convertir bytes a base64url
    registration_data["publicKey"]["challenge"] = bytes_to_base64url(
        registration_data["publicKey"]["challenge"]
    )
    registration_data["publicKey"]["user"]["id"] = bytes_to_base64url(
        registration_data["publicKey"]["user"]["id"]
    )

    return jsonify(registration_data)

@webauthn_bp.route("/register", methods=["POST"])
def register():
    user_id = "user-1"
    data = request.json
    state = session.get("state")
    if not state:
        return jsonify({"success": False, "error": "No registration state"}), 400

    auth_data = server.register_complete(state, data)
    USERS[user_id]["credentials"].append(auth_data)
    return jsonify({"success": True})

# --- Opciones de autenticación ---
@webauthn_bp.route("/auth-options", methods=["GET"])
def auth_options():
    user_id = (12345).to_bytes(length=4, byteorder='big')
    credentials = USERS.get(user_id, {}).get("credentials", [])

    if not credentials:
        return jsonify({"success": False, "error": "No credentials registered for user."}), 400

    try:
        auth_data, state = server.authenticate_begin(credentials)
        session["state"] = state

        auth_data["challenge"] = websafe_encode(auth_data["challenge"]).decode()
        if "allowCredentials" in auth_data:
            for cred in auth_data["allowCredentials"]:
                cred["id"] = websafe_encode(cred["id"]).decode()

        return jsonify(auth_data)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# --- Verificar autenticación ---
@webauthn_bp.route("/verify", methods=["POST"])
def verify():
    user_id = "user-1"
    data = request.json
    state = session.get("state")
    if not state:
        return jsonify({"success": False, "error": "No authentication state"}), 400

    try:
        server.authenticate_complete(state, USERS[user_id]["credentials"], data)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400