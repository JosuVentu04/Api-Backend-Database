"""empty message

Revision ID: b692f70990ea
Revises: 4ca70b1c2efa
Create Date: 2025-11-04 14:32:04.788119

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b692f70990ea'
down_revision = '4ca70b1c2efa'
branch_labels = None
depends_on = None


def upgrade():
    # Eliminamos la columna antigua
    op.drop_column('contrato_compra_venta', 'ultimo_pago_semanal')
    # Creamos la nueva columna con el tipo correcto
    op.add_column('contrato_compra_venta', sa.Column('ultimo_pago_semanal', sa.Numeric(10, 2), nullable=True))

def downgrade():
    op.drop_column('contrato_compra_venta', 'ultimo_pago_semanal')
    op.add_column('contrato_compra_venta', sa.Column('ultimo_pago_semanal', sa.TIMESTAMP(), nullable=True))
    # ### end Alembic commands ###