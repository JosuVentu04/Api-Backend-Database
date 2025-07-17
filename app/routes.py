from flask import Blueprint, jsonify, current_app
from app.models import Empleado, EstadoUsuario
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app import db
from flask import request

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return jsonify({"mensaje": "Hola mundo desde Flask!"})

@main.route('/empleado-demo')
def empleado_demo():
    usuario = {
        "nombre": "Ana",
        "estado_usuario": "ACTIVO"
    }
    return jsonify(usuario)

@main.route("/empleado", methods=["POST"])
def crear_empleado():
    data = request.get_json()

    if not data.get("password"):
        return {"error": "password es requerido"}, 400
    if not data.get("correo"):
        return {"error": "correo es requerido"}, 400

    # 2. Verificar correo duplicado
    if Empleado.query.filter_by(correo=data["correo"]).first():
        return {"error": "correo ya registrado"}, 409

    try:
        # 3. Crear registro
        nuevo_empleado = Empleado(
            nombre=data.get("nombre"),
            estado_usuario=data.get("estado_usuario", EstadoUsuario.ACTIVO),
            correo=data["correo"]
        )
        nuevo_empleado.set_password(data["password"])  # helper que hashea
        db.session.add(nuevo_empleado)
        db.session.commit()

    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Fallo al crear empleado")
        return {"error": "error interno del servidor"}, 500

    return jsonify(
        mensaje="Usuario creado",
        id=nuevo_empleado.id
    ), 201

@main.route('/empleados', methods=['GET'])
def obtener_empleados():
    empleados = Empleado.query.all()  # Trae todos los registros
    lista_empleados = []

    for emp in empleados:
        lista_empleados.append({
            "id": emp.id,
            "nombre": emp.nombre,
            "estado_usuario": emp.estado_usuario.value if emp.estado_usuario else None,
            "correo": emp.correo
              # Si no quieres devolver password, elimínalo aquí
        })

    return jsonify(lista_empleados)