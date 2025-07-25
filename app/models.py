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

    def __repr__(self) -> str:
        return f"<Sucursal {self.id} – {self.nombre}>"


# ──────────────────────────────────────────────
#  Modelo Empleado
# ──────────────────────────────────────────────
class Empleado(db.Model):
    __tablename__ = "empleado"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)

    # ---- verificación de correo ----
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    fecha_verificacion: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    estado_usuario: Mapped[EstadoUsuario] = mapped_column(
        SqlEnum(EstadoUsuario, name="estado_usuario_enum",
                native_enum=False, validate_strings=True),
        default=EstadoUsuario.ACTIVO,
        server_default=text("'ACTIVO'"),
        nullable=False
    )

    correo: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    _password_hash: Mapped[str] = mapped_column("password_hash", String(128), nullable=False)

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
            "estado_usuario": self.estado_usuario.value,
            "sucursal_id": self.sucursal_id,
            "is_verified": self.is_verified           # ← ahora sí lo expones
        }

    def __repr__(self):
        return f"<Empleado {self.id} – {self.correo}>"