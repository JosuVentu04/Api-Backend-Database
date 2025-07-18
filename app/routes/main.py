# app/routes/main.py
from flask import Blueprint, jsonify, request, current_app
from sqlalchemy.exc import SQLAlchemyError
from app import db
from app.models import Empleado, EstadoUsuario, Sucursal, EstadoSucursal

main = Blueprint("main", __name__)

# ──────────────────────────────────────────────
# 0. Hello World
# ──────────────────────────────────────────────
@main.get("/")
def index():
    return jsonify(mensaje="Hola mundo desde Flask!")

# ──────────────────────────────────────────────
# 1.  CRUD  S U C U R S A L
# ──────────────────────────────────────────────
@main.post("/sucursal")
def crear_sucursal():
    data = request.get_json() or {}

    if not data.get("nombre"):
        return {"error": "El nombre de la sucursal es requerido"}, 400
    if not data.get("direccion"):
        return {"error": "La dirección es requerida"}, 400
    if not data.get("numero_telefono"):
        return {"error": "El teléfono es requerido"}, 400

    try:
        nueva = Sucursal(
            nombre=data["nombre"],
            estado_sucursal=EstadoSucursal[data.get("estado_sucursal", "ACTIVA")],
            direccion=data["direccion"],
            numero_telefonico=data["numero_telefono"],
        )
        db.session.add(nueva)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Fallo al crear la sucursal")
        return {"error": "Error interno del servidor"}, 500

    return jsonify(mensaje="Sucursal creada exitosamente", id=nueva.id), 201


@main.get("/sucursales")
def obtener_sucursales():
    sucursales = Sucursal.query.all()
    lista = [
        {
            "id": s.id,
            "nombre": s.nombre,
            "estado_sucursal": s.estado_sucursal.value,
            "direccion": s.direccion,
            "numero_telefonico": s.numero_telefonico,
            "fecha_apertura": s.fecha_apertura.isoformat() if s.fecha_apertura else None,
            "fecha_clausura": s.fecha_clausura.isoformat() if s.fecha_clausura else None,
        }
        for s in sucursales
    ]
    return jsonify(lista)

# ──────────────────────────────────────────────
# 2.  CRUD  E M P L E A D O
# ──────────────────────────────────────────────
@main.post("/empleado")
def crear_empleado():
    data = request.get_json() or {}

    if not data.get("password"):
        return {"error": "password es requerido"}, 400
    if not data.get("correo"):
        return {"error": "correo es requerido"}, 400

    # correo duplicado
    if Empleado.query.filter_by(correo=data["correo"]).first():
        return {"error": "correo ya registrado"}, 409

    try:
        nuevo = Empleado(
            nombre=data.get("nombre"),
            estado_usuario=EstadoUsuario[data.get("estado_usuario", "ACTIVO")],
            correo=data["correo"],
            sucursal_id=data.get("sucursal_id")
        )
        nuevo.set_password(data["password"])
        db.session.add(nuevo)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Fallo al crear empleado")
        return {"error": "error interno del servidor"}, 500

    return jsonify(mensaje="Usuario creado", id=nuevo.id), 201


@main.get("/empleados")
def obtener_empleados():
    empleados = Empleado.query.all()
    lista = [
        {
            "id": e.id,
            "nombre": e.nombre,
            "estado_usuario": e.estado_usuario.value,
            "correo": e.correo,
            "is_verified": e.is_verified
        }
        for e in empleados
    ]
    return jsonify(lista)

# ──────────────────────────────────────────────
# 3.  End-point de demostración
# ──────────────────────────────────────────────
@main.get("/empleado-demo")
def empleado_demo():
    return jsonify(nombre="Ana", estado_usuario="ACTIVO")



