"""Add LogSource.step_id

Revision ID: 545e104c5f5a
Revises: 5677ef75c712
Create Date: 2014-01-15 17:18:53.402012

"""

# revision identifiers, used by Alembic.
revision = '545e104c5f5a'
down_revision = '5677ef75c712'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('logsource', sa.Column('step_id', sa.GUID(), nullable=True))


def downgrade():
    op.drop_column('logsource', 'step_id')
