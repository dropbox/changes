"""Add Snapshot.source_id

Revision ID: 46a612aff7d3
Revises: 2da2dd72d21c
Create Date: 2014-08-12 15:52:28.488096

"""

# revision identifiers, used by Alembic.
revision = '46a612aff7d3'
down_revision = '2da2dd72d21c'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('snapshot', sa.Column('source_id', sa.GUID(), nullable=True))


def downgrade():
    op.drop_column('snapshot', 'source_id')
