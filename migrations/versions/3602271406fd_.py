"""empty message

Revision ID: 3602271406fd
Revises: 8251dd184efd
Create Date: 2025-07-18 18:08:15.106132

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3602271406fd'
down_revision = '8251dd184efd'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('empleado', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email_verificado', sa.Boolean(), server_default=sa.text('false'), nullable=False))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('empleado', schema=None) as batch_op:
        batch_op.drop_column('email_verificado')

    # ### end Alembic commands ###
