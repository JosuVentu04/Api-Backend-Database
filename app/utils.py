from typing import Optional

from flask import current_app
from itsdangerous import (
    URLSafeTimedSerializer,
    BadSignature,
    SignatureExpired
)
import smtplib, ssl
from email.message import EmailMessage
from flask import current_app


# ──────────────────────────────────────────────────────────────
# Helpers internos
# ──────────────────────────────────────────────────────────────
def _get_serializer() -> URLSafeTimedSerializer:
    """
    Devuelve una instancia única de URLSafeTimedSerializer configurada con
    SECRET_KEY y el salt definido en la configuración.
    """
    secret_key: str = current_app.config["SECRET_KEY"]
    salt: str = current_app.config.get("EMAIL_TOKEN_SALT", "email-verification")
    return URLSafeTimedSerializer(secret_key=secret_key, salt=salt)


# ──────────────────────────────────────────────────────────────
# API pública
# ──────────────────────────────────────────────────────────────
def generate_email_token(email: str) -> str:
    """
    Cifra y firma el correo, devolviendo un token seguro que incluye timestamp.
    """
    return _get_serializer().dumps(email)


def confirm_email_token(token: str, max_age: int = 3600) -> Optional[str]:
    """
    Valida el token. Si es correcto y no ha expirado, devuelve el email;
    en caso contrario, devuelve None.

    Parámetros
    ----------
    token : str
        Token recibido, típicamente vía link de verificación.
    max_age : int
        Tiempo máximo de validez en segundos (por defecto 1 h).

    Returns
    -------
    str | None
        El correo extraído o None si el token es inválido/expirado.
    """
    s = _get_serializer()
    try:
        return s.loads(token, max_age=max_age)
    except SignatureExpired:
        current_app.logger.info("Token de verificación expirado")
    except BadSignature:
        current_app.logger.warning("Token manipulado o clave incorrecta")
    return None

def send_email(subject: str, body: str, to: str):
    cfg = current_app.config
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["MAIL_USERNAME"]
    msg["To"]   = to
    msg.set_content(body, subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP(cfg["MAIL_SERVER"], cfg["MAIL_PORT"]) as smtp:
        if cfg["MAIL_USE_TLS"]:
            smtp.starttls(context=context)
        smtp.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
        smtp.send_message(msg)