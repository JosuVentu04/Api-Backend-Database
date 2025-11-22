from alembic import op
import sqlalchemy as sa

"""Agrega campo estado_deuda con ENUM"""

revision = 'edb43d092d2a'
down_revision = '5e92eb52e39d'
branch_labels = None
depends_on = None


def upgrade():
    # 1️⃣ Crear ENUM en PostgreSQL si no existe
    estado_enum = sa.Enum(
        "AL_DIA",
        "ATRASADO",
        "LIQUIDADO",
        name="estado_deuda_enum"
    )
    estado_enum.create(op.get_bind(), checkfirst=True)

    # 2️⃣ Agregar columna con default correctamente en formato SQL
    op.add_column(
        "contrato_compra_venta",
        sa.Column(
            "estado_deuda",
            estado_enum,
            nullable=False,
            server_default=sa.text("'AL_DIA'")
        )
    )


def downgrade():
    # 1️⃣ Quitar la columna
    op.drop_column("contrato_compra_venta", "estado_deuda")

    # 2️⃣ Eliminar tipo ENUM si existe
    estado_enum = sa.Enum(name="estado_deuda_enum")
    estado_enum.drop(op.get_bind(), checkfirst=True)