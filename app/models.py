from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from sqlalchemy import (
    Enum as SqlEnum,
    String,
    DateTime,
    Integer,
    ForeignKey,
    Boolean,
    Text,
    text,
    func,
    Numeric
)
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import generate_password_hash, check_password_hash

from app import db  # importa la instancia creada en app/__init__.py


# ──────────────────────────────────────────────
#  Enumeraciones
# ──────────────────────────────────────────────
class EstadoDispositivo(PyEnum):
    ACTIVO = 'ACTIVO'
    BLOQUEADO = 'BLOQUEADO'
    VENDIDO = 'VENDIDO'
    EN_REVISION = 'EN_REVISION'


class EstadoContrato(PyEnum):
    PENDIENTE = 'PENDIENTE'
    FIRMADO = 'FIRMADO'
    CANCELADO = 'RECHAZADO'


class EstadoUsuario(PyEnum):
    ACTIVO = 'ACTIVO'
    INACTIVO = 'INACTIVO'


class RolesEmpleado(PyEnum):
    ADMIN = 'ADMIN'
    SOPORTE = 'SOPORTE'
    GERENTE = 'GERENTE'
    VENDEDOR = 'VENDEDOR'


class EstadoSucursal(PyEnum):
    ACTIVA = 'ACTIVA'
    CERRADA = 'CERRADA'
    SUSPENDIDA = 'SUSPENDIDA'


class TipoIdentificacion(PyEnum):
    passport = 'passport'
    id_card = 'id_card'
    driver_license = 'driver_license'
    residence_permit = 'residence_permit'
    identity_card = 'identity_card'


class EstadoUsuario(PyEnum):
    ACTIVO = 'ACTIVO'
    INACTIVO = 'INACTIVO'
    MOROSO = 'MOROSO'
    BLOQUEADO = 'BLOQUEADO'
    ELIMINADO = 'ELIMINADO'


def calcular_plan_pago(plan: 'PlanPago', monto_total: Decimal):
    """
    Calcula los pagos semanales de un plan, evitando centavos.

    Args:
        plan (PlanPago): instancia del plan de pago.
        monto_total (Decimal): precio total del dispositivo.

    Returns:
        dict: información del plan con las cuotas calculadas.
    """
    # ✅ Validaciones básicas
    if plan.duracion_semanas <= 0:
        raise ValueError('El plan debe tener al menos 1 semana.')
    if monto_total <= 0:
        raise ValueError('El monto total debe ser mayor a 0.')
    # ✅ Restar pago inicial (si lo hay)
    monto_financiar = monto_total - plan.pago_inicial

    # ✅ Aplicar interés si existe
    if plan.tasa_interes > 0:
        monto_financiar += monto_financiar * (plan.tasa_interes / 100)
    # ✅ Calcular cuota semanal base
    cuota_base = monto_financiar / plan.duracion_semanas

    # ✅ Convertir a Decimal y redondear hacia abajo (sin centavos)
    cuota_entera = cuota_base.quantize(Decimal('1'), rounding=ROUND_DOWN)

    # ✅ Recalcular total pagado en cuotas y ajustar última cuota
    total_cuotas = cuota_entera * plan.duracion_semanas
    diferencia = monto_financiar - total_cuotas

    # Ajustar la última cuota para compensar los centavos perdidos
    ultima_cuota = cuota_entera + diferencia

    # ✅ Crear lista de pagos
    cuotas = [int(cuota_entera)] * (plan.duracion_semanas - 1) + [int(ultima_cuota)]

    return {
        'nombre_plan': plan.nombre_plan,
        'duracion_semanas': plan.duracion_semanas,
        'tasa_interes': plan.tasa_interes,
        'pago_inicial': float(plan.pago_inicial),
        'monto_total': float(monto_total),
        'monto_financiar': float(monto_financiar),
        'cuota_semanal': int(cuota_entera),
        'cuotas': cuotas,
        'total_pagado': float(plan.pago_inicial + sum(cuotas))
    }


# ──────────────────────────────────────────────
#  Modelo Sucursal
# ──────────────────────────────────────────────
class Sucursal(db.Model):
    __tablename__ = 'sucursal'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    nombre: Mapped[str] = mapped_column(String(120), nullable=False, index=True)

    estado_sucursal: Mapped[EstadoSucursal] = mapped_column(
        SqlEnum(
            EstadoSucursal,
            name='estado_sucursal_enum',
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
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    fecha_clausura: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relación ↔ empleados
    empleados: Mapped[list['Empleado']] = relationship(
        'Empleado',
        back_populates='sucursal',
        cascade='all, delete-orphan',
        lazy='selectin'
    )

    def serialize(self) -> dict:
        return {
            'id': self.id,
            'nombre': self.nombre,
            'estado_sucursal': self.estado_sucursal.value,
            'direccion': self.direccion,
            'numero_telefonico': self.numero_telefonico,
            'fecha_apertura': self.fecha_apertura.isoformat()
            if self.fecha_apertura
            else None,
            'fecha_clausura': self.fecha_clausura.isoformat()
            if self.fecha_clausura
            else None
        }

    def __repr__(self) -> str:
        return f"<Sucursal {self.id} – {self.nombre}>"


class Usuario(db.Model):
    __tablename__ = 'usuario'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    primer_nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    apellido_paterno: Mapped[str] = mapped_column(String(120), nullable=False)
    apellido_materno: Mapped[str] = mapped_column(String(120), nullable=True)
    curp: Mapped[str] = mapped_column(String(18), unique=True, nullable=True)
    correo: Mapped[str] = mapped_column(
        String(120), unique=True, nullable=True, index=True
    )
    rfc: Mapped[str] = mapped_column(String(13), unique=True, nullable=True)
    nacionalidad: Mapped[str] = mapped_column(String(50), nullable=True)
    numero_telefonico_adicional: Mapped[str] = mapped_column(String(12), nullable=True)
    numero_telefonico: Mapped[str] = mapped_column(String(12), nullable=True)
    tipo_identificacion: Mapped[TipoIdentificacion] = mapped_column(
        SqlEnum(
            TipoIdentificacion,
            name='tipo_identificacion_enum',
            native_enum=False,
            validate_strings=True
        ),
        nullable=True
    )
    numero_identificacion: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=True
    )
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    fecha_nacimiento: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    estado_usuario: Mapped[EstadoUsuario] = mapped_column(
        SqlEnum(
            EstadoUsuario,
            name='estado_usuario_enum',
            native_enum=False,
            validate_strings=True
        ),
        default=EstadoUsuario.ACTIVO
    )
    notas: Mapped[str] = mapped_column(String(1500), nullable=True)
    datos_biometricos: Mapped[str] = mapped_column(String(1500), nullable=True)
    fotografia_url: Mapped[str] = mapped_column(String(550), nullable=True)

    # Verificación
    verificado: Mapped[bool] = mapped_column(default=False)
    proveedor_verificacion: Mapped[str] = mapped_column(String(50), nullable=True)
    fecha_verificacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relación con domicilio
    domicilios = relationship(
        'Domicilio', back_populates='usuario', cascade='all, delete-orphan'
    )

    score_crediticio: Mapped[int] = mapped_column(Integer, nullable=True)
    credito_aprobado: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text('false'), nullable=False
    )

    def serialize(self) -> dict:
        domicilio = self.domicilios[0] if self.domicilios else None
        return {
            'id': self.id,
            'primer_nombre': self.primer_nombre,
            'apellido_paterno': self.apellido_paterno,
            'apellido_materno': self.apellido_materno,
            'curp': self.curp,
            'rfc': self.rfc,
            'correo': self.correo,
            'numero_telefonico': self.numero_telefonico,
            'numero_telefonico_adicional': self.numero_telefonico_adicional,
            'tipo_identificacion': self.tipo_identificacion.value
            if self.tipo_identificacion
            else None,
            'numero_identificacion': self.numero_identificacion,
            'fecha_nacimiento': self.fecha_nacimiento.isoformat()
            if self.fecha_nacimiento
            else None,
            'estado_usuario': self.estado_usuario.value
            if self.estado_usuario
            else None,
            'nacionalidad': self.nacionalidad,
            'notas': self.notas,
            'verificado': self.verificado,
            'proveedor_verificacion': self.proveedor_verificacion,
            'fecha_verificacion': self.fecha_verificacion.isoformat()
            if self.fecha_verificacion
            else None,
            'fotografia_url': self.fotografia_url,
            'domicilio': domicilio.serialize() if domicilio else None,
            'score_crediticio': self.score_crediticio,
            'credito_aprobado': self.credito_aprobado
        }

    def __repr__(self):
        return f"<Usuario {self.id} – {self.primer_nombre} {self.apellido_paterno}>"


class Domicilio(db.Model):
    __tablename__ = 'domicilio'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey('usuario.id'), nullable=False, unique=True
    )
    direccion: Mapped[str] = mapped_column(String(255))
    colonia: Mapped[str] = mapped_column(String(255))
    ciudad: Mapped[str] = mapped_column(String(100))
    estado: Mapped[str] = mapped_column(String(100))
    codigo_postal: Mapped[str] = mapped_column(String(10))
    tipo: Mapped[str] = mapped_column(
        String(50), nullable=True
    )  # "fiscal", "actual", etc.

    usuario = relationship('Usuario', back_populates='domicilios')

    def serialize(self):
        return {
            'direccion': self.direccion,
            'colonia': self.colonia,
            'ciudad': self.ciudad,
            'estado': self.estado,
            'codigo_postal': self.codigo_postal,
            'tipo': self.tipo
        }


# ──────────────────────────────────────────────
#  Modelo Empleado
# ──────────────────────────────────────────────


class Empleado(db.Model):
    __tablename__ = 'empleado'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    numero_telefonico: Mapped[str] = mapped_column(String(12), nullable=True)

    # ---- verificación de correo ----
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text('false'), nullable=False
    )
    rol: Mapped[RolesEmpleado] = mapped_column(
        SqlEnum(
            RolesEmpleado,
            name='roles_empleado',
            native_enum=False,
            validate_strings=True
        ),
        default=RolesEmpleado.VENDEDOR,
        server_default=text('VENDEDOR'),
        nullable=False
    )
    fecha_verificacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    estado_usuario: Mapped[EstadoUsuario] = mapped_column(
        SqlEnum(
            EstadoUsuario,
            name='estado_usuario_enum',
            native_enum=False,
            validate_strings=True
        ),
        default=EstadoUsuario.ACTIVO,
        server_default=text("'ACTIVO'"),
        nullable=False
    )
    correo_pendiente: Mapped[str] = mapped_column(
        String(120), unique=True, nullable=True, index=True
    )

    correo_token_antiguo: Mapped[str] = mapped_column(String(255), nullable=True)

    correo_token_nuevo: Mapped[str] = mapped_column(String(255), nullable=True)

    correo_antiguo_confirmado: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text('false'), nullable=False
    )

    correo_nuevo_confirmado: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text('false'), nullable=False
    )

    correo_token_expira: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    correo: Mapped[str] = mapped_column(
        String(120), unique=True, nullable=False, index=True
    )

    _password_hash: Mapped[str] = mapped_column(
        'password_hash', String(255), nullable=False
    )

    sucursal_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('sucursal.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    sucursal = relationship('Sucursal', back_populates='empleados', lazy='joined')

    # ------------------------------- helpers -------------------------------
    def set_password(self, raw: str) -> None:
        self._password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self._password_hash, raw)

    def serialize(self) -> dict:
        return {
            'id': self.id,
            'nombre': self.nombre,
            'correo': self.correo,
            'numero_telefonico': self.numero_telefonico,
            'estado_usuario': self.estado_usuario.value,
            'sucursal_id': self.sucursal_id,
            'is_verified': self.is_verified,  # ← ahora sí lo expones
            'rol': self.rol.value
        }

    def __repr__(self):
        return f"<Empleado {self.id} – {self.correo}>"


class Catalogo_Modelos(db.Model):
    __tablename__ = 'catalogo_modelos'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    marca: Mapped[str] = mapped_column(String(120), nullable=False)
    modelo: Mapped[str] = mapped_column(String(120), nullable=False)
    almacenamiento: Mapped[str] = mapped_column(String(120), nullable=False)
    anio: Mapped[str] = mapped_column(String(120), nullable=False)
    ram: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[str] = mapped_column(
        String(1500), nullable=True, default='Celular de alta calidad'
    )
    color: Mapped[str] = mapped_column(String(120), nullable=True)
    dual_sim: Mapped[bool] = mapped_column(
        default=False, server_default=text('false'), nullable=True
    )
    red_movil: Mapped[str] = mapped_column(String(120), nullable=True)
    version_android: Mapped[str] = mapped_column(String(120), nullable=True)
    procesador: Mapped[str] = mapped_column(String(120), nullable=True)
    velocidad_procesador: Mapped[str] = mapped_column(String(120), nullable=True)
    cantidad_nucleos: Mapped[str] = mapped_column(String(120), nullable=True)
    tamanio_pantalla: Mapped[str] = mapped_column(String(120), nullable=True)
    tipo_resolucion: Mapped[str] = mapped_column(String(120), nullable=True)
    frecuencia_actualizacion_pantalla: Mapped[str] = mapped_column(
        String(120), nullable=True
    )
    resolucion_camara_trasera_principal: Mapped[str] = mapped_column(
        String(120), nullable=True
    )
    resolucion_camara_frontal_principal: Mapped[str] = mapped_column(
        String(120), nullable=True
    )
    capacidad_bateria: Mapped[str] = mapped_column(String(120), nullable=True)
    carga_rapida: Mapped[bool] = mapped_column(
        default=False, server_default=text('false'), nullable=True
    )
    huella_dactilar: Mapped[bool] = mapped_column(
        default=False, server_default=text('false'), nullable=True
    )
    resistencia_salpicaduras: Mapped[bool] = mapped_column(
        default=False, server_default=text('false'), nullable=True
    )
    resistencia_agua: Mapped[bool] = mapped_column(
        default=False, server_default=text('false'), nullable=True
    )
    resistencia_polvo: Mapped[bool] = mapped_column(
        default=False, server_default=text('false'), nullable=True
    )
    resistencia_caidas: Mapped[bool] = mapped_column(
        default=False, server_default=text('false'), nullable=True
    )
    precio: Mapped[float] = mapped_column(nullable=True)
    imagen: Mapped[str] = mapped_column(String(550), nullable=True)
    fecha_creacion: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
    fecha_actualizacion: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=func.now()
    )

    def serialize_basic(self) -> dict:
        """Serialización básica para listado"""
        return {
            'id': self.id,
            'marca': self.marca,
            'modelo': self.modelo,
            'almacenamiento': self.almacenamiento,
            'anio': self.anio,
            'ram': self.ram,
            'descripcion': self.descripcion,
            'imagen': self.imagen,
            'precio': self.precio
        }

    def serialize(self) -> dict:
        """Serialización completa para detalle"""
        return {
            'id': self.id,
            'marca': self.marca,
            'modelo': self.modelo,
            'almacenamiento': self.almacenamiento,
            'anio': self.anio,
            'ram': self.ram,
            'descripcion': self.descripcion,
            'color': self.color,
            'dual_sim': self.dual_sim,
            'red_movil': self.red_movil,
            'version_android': self.version_android,
            'procesador': self.procesador,
            'velocidad_procesador': self.velocidad_procesador,
            'cantidad_nucleos': self.cantidad_nucleos,
            'tamanio_pantalla': self.tamanio_pantalla,
            'tipo_resolucion': self.tipo_resolucion,
            'frecuencia_actualizacion_pantalla': self.frecuencia_actualizacion_pantalla,
            'resolucion_camara_trasera_principal': self.resolucion_camara_trasera_principal,
            'resolucion_camara_frontal_principal': self.resolucion_camara_frontal_principal,
            'capacidad_bateria': self.capacidad_bateria,
            'carga_rapida': self.carga_rapida,
            'huella_dactilar': self.huella_dactilar,
            'resistencia_salpicaduras': self.resistencia_salpicaduras,
            'resistencia_agua': self.resistencia_agua,
            'resistencia_polvo': self.resistencia_polvo,
            'resistencia_caidas': self.resistencia_caidas,
            'imagen': self.imagen,
            'precio': self.precio,
            'fecha_creacion': self.fecha_creacion.isoformat()
            if self.fecha_creacion
            else None,
            'fecha_actualizacion': self.fecha_actualizacion.isoformat()
            if self.fecha_actualizacion
            else None
        }

    def __repr__(self):
        return f"<Dispositivo {self.id} – {self.modelo}>"


class ConsultasVerificacion(db.Model):
    __tablename__ = 'consultas_verificacion'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empleado_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('empleado.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    empleado = relationship('Empleado', lazy='joined')

    usuario_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey('usuario.id', ondelete='CASCADE'),
        nullable=True, index=True
    )
    usuario = relationship('Usuario', lazy='joined')

    primer_nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    apellido_paterno: Mapped[str] = mapped_column(String(120), nullable=False)

    fecha_consulta: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    motivo_consulta: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    resultado_consulta: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    def serialize(self) -> dict:
        return {
            'id': self.id,
            'empleado_id': self.empleado_id,
            'usuario_id': self.usuario_id,
            'session_id': self.session_id,
            'fecha_consulta': self.fecha_consulta.isoformat() if self.fecha_consulta else None,
            'motivo_consulta': self.motivo_consulta,
            'resultado_consulta': self.resultado_consulta
        }

    def __repr__(self):
        return f"<ConsultaVerificacion {self.id} – Empleado {self.empleado_id} – Usuario {self.usuario_id}>"


# ──────────────────────────────────────────────
#  Contrato Consulta Buró
# ──────────────────────────────────────────────

class ContratoConsultaBuro(db.Model):
    __tablename__ = 'contrato_consulta_buro'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('usuario.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    empleado_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('empleado.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    contrato_url: Mapped[str] = mapped_column(String(550), nullable=False)
    hash_contrato: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contrato_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    estado_contrato: Mapped[EstadoContrato] = mapped_column(
        db.Enum(EstadoContrato, name='estado_contrato_enum', native_enum=False, validate_strings=True),
        default=EstadoContrato.PENDIENTE,
        server_default=text("'PENDIENTE'")
    )

    fecha_firma: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    nombre: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    apellido: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    def serialize(self) -> dict:
        return {
            'id': self.id,
            'cliente_id': self.cliente_id,
            'empleado_id': self.empleado_id,
            'contrato_url': self.contrato_url,
            'hash_contrato': self.hash_contrato,
            'contrato_html': self.contrato_html,
            'estado_contrato': self.estado_contrato.value if self.estado_contrato else None,
            'fecha_firma': self.fecha_firma.isoformat() if self.fecha_firma else None
        }


# ──────────────────────────────────────────────
#  Dispositivo
# ──────────────────────────────────────────────

class Dispositivo(db.Model):
    __tablename__ = 'dispositivo'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    modelo: Mapped[str] = mapped_column(String(120), nullable=False)
    imei: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    precio: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    estado: Mapped[EstadoDispositivo] = mapped_column(
        db.Enum(EstadoDispositivo), default=EstadoDispositivo.ACTIVO, nullable=False
    )

    usuario_id: Mapped[Optional[int]] = mapped_column(ForeignKey('usuario.id'), nullable=True)
    usuario = relationship('Usuario', backref=db.backref('dispositivos', lazy=True))

    contrato_id: Mapped[Optional[int]] = mapped_column(ForeignKey('contrato_compra_venta.id'), nullable=True)
    contrato = relationship('ContratoCompraVenta', back_populates='dispositivos')

    fecha_registro: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    fecha_actualizacion: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=func.now())

    def serialize(self) -> dict:
        return {
            'id': self.id,
            'modelo': self.modelo,
            'imei': self.imei,
            'precio': float(self.precio),
            'estado': self.estado.value,
            'usuario_id': self.usuario_id,
            'contrato_id': self.contrato_id,
            'fecha_registro': self.fecha_registro.isoformat() if self.fecha_registro else None,
            'fecha_actualizacion': self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None
        }

    def __repr__(self):
        return f"<Dispositivo {self.modelo} - IMEI: {self.imei}>"


# ──────────────────────────────────────────────
#  Contrato Compra-Venta
# ──────────────────────────────────────────────

class ContratoCompraVenta(db.Model):
    __tablename__ = 'contrato_compra_venta'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey('usuario.id'), nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    detalles: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    empleado_id: Mapped[Optional[int]] = mapped_column(ForeignKey('empleado.id'), nullable=True)
    contrato_url: Mapped[Optional[str]] = mapped_column(String(550), nullable=True)
    hash_contrato: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contrato_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estado_contrato: Mapped[EstadoContrato] = mapped_column(
        db.Enum(EstadoContrato, name='estado_contrato_enum', native_enum=False, validate_strings=True),
        default=EstadoContrato.PENDIENTE, server_default=text("'PENDIENTE'"), nullable=False
    )
    fecha_firma: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    precio_total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    pago_inicial: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    plan_pago_id: Mapped[int] = mapped_column(ForeignKey('plan_pago.id'), nullable=False)
    pago_semanal: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    ultimo_pago_semanal: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    num_pagos_semanales: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    proximo_pago_fecha: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    usuario = relationship('Usuario', backref=db.backref('contratos_compra_venta', lazy=True))
    dispositivos = relationship('Dispositivo', back_populates='contrato', cascade='all, delete-orphan')
    
    def serialize(self) -> dict:
        return {
            'id': self.id,
            'cliente_id': self.cliente_id,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'detalles': self.detalles,
            'empleado_id': self.empleado_id,
            'contrato_url': self.contrato_url,
            'hash_contrato': self.hash_contrato,
            'contrato_html': self.contrato_html,
            'estado_contrato': self.estado_contrato.value if self.estado_contrato else None,
            'fecha_firma': self.fecha_firma.isoformat() if self.fecha_firma else None,
            'precio_total': float(self.precio_total),
            'pago_inicial': float(self.pago_inicial),
            'plan_pago_id': self.plan_pago_id,
            'pago_semanal': float(self.pago_semanal) if self.pago_semanal is not None else None,
            'ultimo_pago_semanal': float(self.ultimo_pago_semanal) if self.ultimo_pago_semanal is not None else None,
            'num_pagos_semanales': self.num_pagos_semanales,
            'proximo_pago_fecha': self.proximo_pago_fecha.isoformat() if self.proximo_pago_fecha else None
        }

    def __repr__(self):
        return (
            f"<Contrato {self.id} - Cliente ID: {self.cliente_id} - "
            f"Precio Total: {self.precio_total} - Pago Inicial: {self.pago_inicial} - "
            f"Pago Semanal: {self.pago_semanal} - Num Pagos: {self.num_pagos_semanales}>"
        )


# ──────────────────────────────────────────────
#  Plan de Pago
# ──────────────────────────────────────────────

class PlanPago(db.Model):
    __tablename__ = 'plan_pago'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre_plan: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duracion_semanas: Mapped[int] = mapped_column(Integer, nullable=False)
    tasa_interes: Mapped[float] = mapped_column(Numeric, nullable=False)
    pago_inicial: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    activo: Mapped[bool] = mapped_column(db.Boolean, default=True, server_default=text('true'), nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    tratos = relationship('ContratoCompraVenta', backref='plan_pago', lazy=True)

    def serialize(self) -> dict:
        return {
            'id': self.id,
            'nombre_plan': self.nombre_plan,
            'descripcion': self.descripcion,
            'duracion_semanas': self.duracion_semanas,
            'tasa_interes': float(self.tasa_interes),
            'pago_inicial': str(self.pago_inicial),
            'activo': self.activo,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None
        }