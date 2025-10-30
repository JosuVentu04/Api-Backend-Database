from typing import Optional
from app.models import PlanPago
from flask import current_app
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from email.message import EmailMessage
import smtplib, ssl
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

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
    Calcula las cuotas de un plan de pago, permitiendo un pago inicial variable.
    Redondea correctamente los valores para evitar errores de conversión.
    """

    # Si no se pasa pago_inicial, usar el del plan
    pago_inicial = Decimal(str(pago_inicial if pago_inicial is not None else plan.pago_inicial))

    if plan.duracion_semanas <= 0:
        raise ValueError("El plan debe tener al menos 1 semana.")
    if monto_total <= 0:
        raise ValueError("El monto total debe ser mayor a 0.")
    if pago_inicial < 0 or pago_inicial > monto_total:
        raise ValueError("El pago inicial debe estar entre 0 y el monto total.")

    # Tasa de interés
    tasa_interes = Decimal(str(plan.tasa_interes)) / Decimal('100')

    # Monto a financiar
    monto_financiar = monto_base - pago_inicial
    if tasa_interes > 0:
        monto_financiar *= (Decimal('1') + tasa_interes)

    # Calcular cuota base (sin redondear aún)
    cuota_base = monto_financiar / Decimal(plan.duracion_semanas)

    # Redondear a 2 decimales (normal financiero)
    cuota_redondeada = int(cuota_base.to_integral_value(rounding=ROUND_HALF_UP))

    # Calcular el total de las cuotas y la diferencia
    total_cuotas = cuota_redondeada * plan.duracion_semanas

    # Ajustar la última cuota con la diferencia
    ultima_cuota = int(monto_financiar - cuota_redondeada * (plan.duracion_semanas - 1))

    # Generar la lista de cuotas
    cuotas = [cuota_redondeada] * (plan.duracion_semanas - 1) + [ultima_cuota]

    # Resultado final
    return {
        "nombre_plan": plan.nombre_plan,
        "duracion_semanas": plan.duracion_semanas,
        "tasa_interes": float(plan.tasa_interes),
        "pago_inicial": float(pago_inicial),
        "monto_total": float(monto_total),
        "monto_financiar": float(monto_financiar.quantize(Decimal("0.01"))),
        "cuota_semanal": float(cuota_redondeada),
        "cuotas": cuotas,
        "total_pagado": float(pago_inicial + sum(Decimal(str(c)) for c in cuotas)),
    }