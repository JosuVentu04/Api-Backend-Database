from flask import Blueprint, jsonify, request, current_app, redirect
from sqlalchemy.exc import SQLAlchemyError
from app.models import Catalogo_Modelos
from app import db
import sqlalchemy.exc

dispositivos = Blueprint("dispositivos", __name__, url_prefix="/devices")

@dispositivos.post("/nuevo-modelo")
def crear_modelo():
    data = request.get_json() or {}

    campos_obligatorios = ["marca", "modelo", "almacenamiento", "anio", "ram"]
    errores = [
        f"El campo '{campo}' es requerido" for campo in campos_obligatorios if not data.get(campo)
    ]
    if errores:
        return {"error": errores}, 400
    try:
        nuevo_modelo = Catalogo_Modelos(
            marca=data["marca"],
            modelo=data["modelo"],
            almacenamiento=data["almacenamiento"],
            anio=data["anio"], 
            ram=data["ram"],
            descripcion=data.get("descripcion"),
            color=data.get("color"),
            dual_sim=data.get("dual_sim"),
            red_movil=data.get("red_movil"),
            version_android=data.get("version_android"),
            procesador=data.get("procesador"),
            velocidad_procesador=data.get("velocidad_procesador"),
            cantidad_nucleos=data.get("cantidad_nucleos"),
            tamanio_pantalla=data.get("tamanio_pantalla"),
            tipo_resolucion=data.get("tipo_resolucion"),
            frecuencia_actualizacion_pantalla=data.get("frecuencia_actualizacion_pantalla"),
            resolucion_camara_trasera_principal=data.get("resolucion_camara_trasera_principal"),
            resolucion_camara_frontal_principal=data.get("resolucion_camara_frontal_principal"),
            capacidad_bateria=data.get("capacidad_bateria"),
            carga_rapida=data.get("carga_rapida"),
            huella_dactilar=data.get("huella_dactilar"),
            resistencia_salpicaduras=data.get("resistencia_salpicaduras"),
            resistencia_agua=data.get("resistencia_agua"),
            resistencia_polvo=data.get("resistencia_polvo"),
            resistencia_caidas=data.get("resistencia_caidas"),
            imagen=data.get("imagen", "")
            # fecha_creacion y fecha_actualizacion no son necesarios aquí, los maneja el modelo
        )
        db.session.add(nuevo_modelo)
        db.session.commit()
        db.session.refresh(nuevo_modelo)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Fallo al crear el modelo")
        return {"error": "Error interno del servidor"}, 500

    return jsonify(mensaje="Modelo creado exitosamente", id=nuevo_modelo.id), 201

@dispositivos.put("/editar-modelo/<int:modelo_id>")
def editar_modelo(modelo_id):
    modelo = Catalogo_Modelos.query.get_or_404(modelo_id)
    data = request.get_json() or {}

    # Actualiza solo los campos recibidos en el JSON,
    # Sin tocar los que no vienen.
    atributos_actualizables = [
        "marca", "modelo", "almacenamiento", "anio", "ram", "descripcion", "imagen",
        "color", "dual_sim", "red_movil", "version_android", "procesador",
        "velocidad_procesador", "cantidad_nucleos", "tamanio_pantalla",
        "tipo_resolucion", "frecuencia_actualizacion_pantalla",
        "resolucion_camara_trasera_principal", "resolucion_camara_frontal_principal",
        "capacidad_bateria", "carga_rapida", "huella_dactilar",
        "resistencia_salpicaduras", "resistencia_agua",
        "resistencia_polvo", "resistencia_caidas"
    ]
    for atributo in atributos_actualizables:
        if atributo in data:
            setattr(modelo, atributo, data[atributo])

    # Actualiza la fecha actualización (si la tienes)
    # SQLAlchemy puede hacerlo automáticamente con onupdate, pero lo pones manualmente si quieres.
    # modelo.fecha_actualizacion = datetime.utcnow()

    try:
        db.session.commit()
        db.session.refresh(modelo)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Fallo al editar el modelo")
        return {"error": "Error interno del servidor"}, 500

    return jsonify({
        "mensaje": "Modelo editado exitosamente",
        "modelo": modelo.serialize()   # Retorna el modelo actualizado
    }), 200
        

@dispositivos.get("/catalogo-modelos")
def listar_modelos():
    modelos = Catalogo_Modelos.query.all()
    return jsonify([m.serialize_basic() for m in modelos])

@dispositivos.get("/catalogo-modelos/<int:modelo_id>")
def obtener_modelo(modelo_id):
    modelo = Catalogo_Modelos.query.get_or_404(modelo_id)
    return jsonify(modelo.serialize())