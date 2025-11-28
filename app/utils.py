from typing import Optional
from app.models import PlanPago
from flask import current_app
from cryptography.fernet import Fernet
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from email.message import EmailMessage
import smtplib, ssl
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
import os

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
    

def calcular_plan_pago(plan: PlanPago, monto_total: Decimal, pago_inicial: Decimal = None, monto_base: Decimal = None):
    """
    Calcula las cuotas de un plan de pago con pagos enteros.
    Ajusta la última cuota para que el total sea exacto.
    """

    # Si no se pasa pago_inicial, usar el del plan
    pago_inicial = Decimal(str(pago_inicial if pago_inicial is not None else plan.pago_inicial))

    if plan.duracion_semanas <= 0:
        raise ValueError("El plan debe tener al menos 1 semana.")
    if monto_total <= 0:
        raise ValueError("El monto total debe ser mayor a 0.")
    if pago_inicial < 0 or pago_inicial > monto_total:
        raise ValueError("El pago inicial debe estar entre 0 y el monto total.")

    # Tasa de interés (ejemplo: 10 → 0.10)
    tasa_interes = Decimal(str(plan.tasa_interes)) / Decimal('100')

    # Calcular el monto a financiar (usando monto_total si monto_base no se pasa)
    monto_financiar = (monto_base) - pago_inicial

    # Aplicar interés si existe
    if tasa_interes > 0:
        monto_financiar *= (Decimal('1') + tasa_interes)

    # Asegurar que trabajamos solo con enteros (redondeo normal)
    monto_financiar = monto_financiar.to_integral_value(rounding=ROUND_HALF_UP)

    # Calcular cuota base entera
    cuota_base = monto_financiar // plan.duracion_semanas  # división entera
    residuo = monto_financiar % plan.duracion_semanas      # diferencia que queda

    # Generar cuotas: todas iguales, y repartir el residuo en la última
    cuotas = [int(cuota_base)] * plan.duracion_semanas
    cuotas[-1] += int(residuo)  # última cuota ajustada

    # Resultado final
    total_pagado = pago_inicial + sum(cuotas)

    return {
        "nombre_plan": plan.nombre_plan,
        "duracion_semanas": plan.duracion_semanas,
        "tasa_interes": float(plan.tasa_interes),
        "pago_inicial": int(pago_inicial),
        "monto_total": int(monto_total),
        "monto_financiar": int(monto_financiar),
        "cuota_semanal": int(cuota_base),
        "cuotas": cuotas,
        "total_pagado": int(total_pagado),
    }
    
def get_fernet():
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise ValueError("ENCRYPTION_KEY no está definida")
    return Fernet(key)


def encrypt_data(data):
    f = get_fernet()

    if data is None:
        return None

    # convertir string a bytes
    if isinstance(data, str):
        data = data.encode()

    return f.encrypt(data)

def decrypt_data(data: bytes) -> bytes:
    """
    Recibe bytes encriptados y devuelve bytes desencriptados.
    """
    f = get_fernet()
    return f.decrypt(data)