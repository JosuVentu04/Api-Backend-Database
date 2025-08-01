from typing import Optional

from flask import current_app
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from email.message import EmailMessage
import smtplib, ssl

# ──────────────────────────────────────────────
# 1.  TOKENS DE VERIFICACIÓN
# ──────────────────────────────────────────────
_SALT = "email-verification"          # usa el mismo en dumps y loads


def _get_serializer() -> URLSafeTimedSerializer:
    """
    Serializer configurado con SECRET_KEY y salt fijo.
    Llamar SIEMPRE a esta función, no crear instancias manualmente.
    """
    secret = current_app.config["SECRET_KEY"]     # clave única de la app
    return URLSafeTimedSerializer(secret, salt=_SALT)


def generate_email_token(email: str) -> str:
    """Devuelve un token firmado que contiene el correo y timestamp."""
    return _get_serializer().dumps(email)


def confirm_email_token(token: str, max_age: int = 86400) -> Optional[str]:
    """
    Valida el token.  Si es correcto y no ha expirado, devuelve el correo.
    Si falla devuelve None.
    """
    try:
        return _get_serializer().loads(token, max_age=max_age)
    except SignatureExpired:
        current_app.logger.info("Token expirado")
    except BadSignature:
        current_app.logger.warning("Token inválido/manipulado")
    return None


# ──────────────────────────────────────────────
# 2.  ENVÍO DE CORREO
# ──────────────────────────────────────────────
def send_email(subject: str, html_body: str, to: str):
    """
    Envía un e-mail HTML usando los parámetros de configuración SMTP:

        MAIL_SERVER
        MAIL_PORT
        MAIL_USERNAME
        MAIL_PASSWORD
        MAIL_USE_TLS (bool)

    Si estás en desarrollo y no tienes SMTP, reemplaza el bloque
    `with smtplib…` por un simple `current_app.logger.info(...)`.
    """
    import logging
    cfg = current_app.config

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["MAIL_USERNAME"]
    msg["To"] = to
    msg.set_content(html_body, subtype="html")

    print(f"Tratando de enviar email a {to} con asunto '{subject}'")

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(cfg["MAIL_SERVER"], cfg["MAIL_PORT"]) as smtp:
            if cfg.get("MAIL_USE_TLS", False):
                smtp.starttls(context=context)
            smtp.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
            smtp.send_message(msg)
        print("Correo enviado correctamente.")
    except Exception as e:
        logging.error(f"Error enviando email a {to}: {e}", exc_info=True)
        print(f"[ERROR SEND_EMAIL]: {e}")
        # Opcional: lanzar la excepción para que el endpoint capture y maneje el error
        raise

        
def generate_email_change_token(email, purpose):
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return s.dumps(email, salt=f"email-change-{purpose}")

def confirm_email_change_token(token, purpose, max_age=86400):
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        email = s.loads(token, salt=f"email-change-{purpose}", max_age=max_age)
        return email
    except (SignatureExpired, BadSignature):
        return None
