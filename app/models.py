from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Enum as SqlEnum, String, DateTime, Integer, ForeignKey, Boolean,
    text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import generate_password_hash, check_password_hash  

from app import db   # importa la instancia creada en app/__init__.py 


# ──────────────────────────────────────────────
#  Enumeraciones
# ──────────────────────────────────────────────
class EstadoUsuario(PyEnum):
    ACTIVO   = "ACTIVO"
    INACTIVO = "INACTIVO"

class RolesEmpleado(PyEnum):
    ADMIN = "ADMIN"
    SOPORTE = "SOPORTE"
    GERENTE = "GERENTE"
    VENDEDOR = "VENDEDOR"

class EstadoSucursal(PyEnum):
    ACTIVA     = "ACTIVA"
    CERRADA    = "CERRADA"
    SUSPENDIDA = "SUSPENDIDA" 


# ──────────────────────────────────────────────
#  Modelo Sucursal
# ──────────────────────────────────────────────
class Sucursal(db.Model):
    __tablename__ = "sucursal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    nombre: Mapped[str] = mapped_column(
        String(120), nullable=False, index=True
    )

    estado_sucursal: Mapped[EstadoSucursal] = mapped_column(
        SqlEnum(
            EstadoSucursal,
            name="estado_sucursal_enum",
            native_enum=False,
            validate_strings=True
        ),
        default=EstadoSucursal.ACTIVA,
        server_default=text("'ACTIVA'"),
        nullable=False
    )

    direccion: Mapped[str] = mapped_column(String(255), nullable=False)
    numero_telefonico: Mapped[str] = mapped_column(String(12), nullable=False)

    fecha_apertura: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=True
    )
    fecha_clausura: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relación ↔ empleados
    empleados: Mapped[list["Empleado"]] = relationship(
        "Empleado",
        back_populates="sucursal",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    def serialize(self) -> dict:
        return {
        "id": self.id,
        "nombre": self.nombre,
        "estado_sucursal": self.estado_sucursal.value,
        "direccion": self.direccion,
        "numero_telefonico": self.numero_telefonico,
        "fecha_apertura": self.fecha_apertura.isoformat() if self.fecha_apertura else None,
        "fecha_clausura": self.fecha_clausura.isoformat() if self.fecha_clausura else None,
    }

    def __repr__(self) -> str:
        return f"<Sucursal {self.id} – {self.nombre}>"


# ──────────────────────────────────────────────
#  Modelo Empleado
# ──────────────────────────────────────────────
class Empleado(db.Model):
    __tablename__ = "empleado"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    numero_telefonico: Mapped[str] = mapped_column(String(12), nullable=True)

    # ---- verificación de correo ----
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    rol: Mapped[RolesEmpleado] = mapped_column(
        SqlEnum(RolesEmpleado, name="roles_empleado", native_enum=False, validate_strings=True), 
        default=RolesEmpleado.VENDEDOR, 
        server_default=text("VENDEDOR"),
        nullable=False)
    fecha_verificacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    estado_usuario: Mapped[EstadoUsuario] = mapped_column(
        SqlEnum(EstadoUsuario, name="estado_usuario_enum",
                native_enum=False, validate_strings=True),
        default=EstadoUsuario.ACTIVO,
        server_default=text("'ACTIVO'"),
        nullable=False
    )
    correo_pendiente: Mapped[str] = mapped_column(String(120), unique=True, nullable=True, index=True)
    
    correo_token_antiguo: Mapped[str] = mapped_column(String(255), nullable=True)
    
    correo_token_nuevo: Mapped[str] = mapped_column(String(255), nullable=True)
    
    correo_antiguo_confirmado: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    
    correo_nuevo_confirmado: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    
    correo_token_expira: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    correo: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    
    _password_hash: Mapped[str] = mapped_column("password_hash", String(255), nullable=False)

    sucursal_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sucursal.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sucursal = relationship("Sucursal", back_populates="empleados", lazy="joined")

    # ------------------------------- helpers -------------------------------
    def set_password(self, raw: str) -> None:
        self._password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self._password_hash, raw)

    def serialize(self) -> dict:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "correo": self.correo,
            "numero_telefonico": self.numero_telefonico,
            "estado_usuario": self.estado_usuario.value,
            "sucursal_id": self.sucursal_id,
            "is_verified": self.is_verified,           # ← ahora sí lo expones
            "rol": self.rol.value
        }

    def __repr__(self):
        return f"<Empleado {self.id} – {self.correo}>"
    
class Catalogo_Modelos(db.Model):
    __tablename__ = "catalogo_modelos"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    marca: Mapped[str] = mapped_column(String(120), nullable=False)
    modelo: Mapped[str] = mapped_column(String(120), nullable=False)
    almacenamiento: Mapped[str] = mapped_column(String(120), nullable=False)
    anio: Mapped[str] = mapped_column(String(120), nullable= False)
    ram: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(1500), nullable=True, default="Celular de alta calidad")
    color: Mapped[str] = mapped_column(String(120), nullable=True)
    dual_sim: Mapped[bool] = mapped_column(default=False, server_default=text("false"), nullable=True)
    red_movil: Mapped[str] = mapped_column(String(120), nullable=True)
    version_android: Mapped[str] = mapped_column(String(120), nullable=True)
    procesador: Mapped[str] = mapped_column(String(120), nullable=True)
    velocidad_procesador: Mapped[str] = mapped_column(String(120), nullable=True)
    cantidad_nucleos: Mapped[str] = mapped_column(String(120), nullable=True)
    tamanio_pantalla: Mapped[str] = mapped_column(String(120), nullable=True)
    tipo_resolucion: Mapped[str] = mapped_column(String(120), nullable=True)
    frecuencia_actualizacion_pantalla: Mapped[str] = mapped_column(String(120), nullable=True)
    resolucion_camara_trasera_principal: Mapped[str] = mapped_column(String(120), nullable=True)
    resolucion_camara_frontal_principal: Mapped[str] = mapped_column(String(120), nullable=True)
    capacidad_bateria: Mapped[str] = mapped_column(String(120), nullable=True)
    carga_rapida: Mapped[bool] = mapped_column(default=False, server_default=text("false"), nullable=True)
    huella_dactilar: Mapped[bool] = mapped_column(default=False, server_default=text("false"), nullable=True)
    resistencia_salpicaduras: Mapped[bool] = mapped_column(default=False, server_default=text("false"), nullable=True)
    resistencia_agua: Mapped[bool] = mapped_column(default=False, server_default=text("false"), nullable=True)
    resistencia_polvo: Mapped[bool] = mapped_column(default=False, server_default=text("false"), nullable=True)
    resistencia_caidas: Mapped[bool] = mapped_column(default=False, server_default=text("false"), nullable=True)
    imagen: Mapped[str] = mapped_column(String(550), nullable=True)
    fecha_creacion: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())
    fecha_actualizacion: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now()
    ) 
    def serialize_basic(self) -> dict:
        """Serialización básica para listado"""
        return {
            "id": self.id,
            "marca": self.marca,
            "modelo": self.modelo,
            "almacenamiento": self.almacenamiento,
            "anio": self.anio,
            "ram": self.ram,
            "descripcion": self.descripcion,
            "imagen": self.imagen,
        }

    def serialize(self) -> dict:
        """Serialización completa para detalle"""
        return {
            "id": self.id,
            "marca": self.marca,
            "modelo": self.modelo,
            "almacenamiento": self.almacenamiento,
            "anio": self.anio,
            "ram": self.ram,
            "descripcion": self.descripcion,
            "color": self.color,
            "dual_sim": self.dual_sim,
            "red_movil": self.red_movil,
            "version_android": self.version_android,
            "procesador": self.procesador,
            "velocidad_procesador": self.velocidad_procesador,
            "cantidad_nucleos": self.cantidad_nucleos,
            "tamanio_pantalla": self.tamanio_pantalla,
            "tipo_resolucion": self.tipo_resolucion,
            "frecuencia_actualizacion_pantalla": self.frecuencia_actualizacion_pantalla,
            "resolucion_camara_trasera_principal": self.resolucion_camara_trasera_principal,
            "resolucion_camara_frontal_principal": self.resolucion_camara_frontal_principal,
            "capacidad_bateria": self.capacidad_bateria,
            "carga_rapida": self.carga_rapida,
            "huella_dactilar": self.huella_dactilar,
            "resistencia_salpicaduras": self.resistencia_salpicaduras,
            "resistencia_agua": self.resistencia_agua,
            "resistencia_polvo": self.resistencia_polvo,
            "resistencia_caidas": self.resistencia_caidas,
            "imagen": self.imagen,
            "fecha_creacion": self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            "fecha_actualizacion": self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None,
        }

    def __repr__(self):
        return f"<Dispositivo {self.id} – {self.modelo}>"