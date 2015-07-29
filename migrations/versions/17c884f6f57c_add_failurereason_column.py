"""add failurereason column

Revision ID: 17c884f6f57c
Revises: 3cf79ad9bde
Create Date: 2015-07-29 08:22:59.755597

"""

# revision identifiers, used by Alembic.
revision = '17c884f6f57c'
down_revision = '3cf79ad9bde'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column(
        'failurereason', 
        sa.Column('data', sa.JSONEncodedDict(), nullable=True))


def downgrade():
    op.drop_column('failurereason', 'data')
