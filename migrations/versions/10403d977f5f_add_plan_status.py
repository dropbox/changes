"""Add Plan.status

Revision ID: 10403d977f5f
Revises: 57e4a0553903
Create Date: 2014-08-27 11:56:07.902348

"""

# revision identifiers, used by Alembic.
revision = '10403d977f5f'
down_revision = '57e4a0553903'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('plan', sa.Column('status', sa.Enum(), server_default='1', nullable=False))


def downgrade():
    op.drop_column('plan', 'status')
