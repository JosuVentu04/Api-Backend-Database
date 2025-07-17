from app import db
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Enum, String
from enum import Enum as PyEnum

class EstadoUsuario(PyEnum):
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"


class Empleado(db.Model):
    __tablename__ = 'empleado_sucursal'

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    estado_usuario: Mapped[EstadoUsuario] = mapped_column(
        Enum(EstadoUsuario, name="estado_usuario_enum"), 
        default=EstadoUsuario.ACTIVO,
        nullable=False
    )
    correo: Mapped[str] = mapped_column(String(120), nullable=False)
    password: Mapped[str] = mapped_column(String(128), nullable=False)

    def serialize(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "correo": self.correo
        }