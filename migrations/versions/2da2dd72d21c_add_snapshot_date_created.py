"""Add Snapshot.date_created

Revision ID: 2da2dd72d21c
Revises: 2191c871434
Create Date: 2014-08-08 14:29:38.740485

"""

# revision identifiers, used by Alembic.
revision = '2da2dd72d21c'
down_revision = '2191c871434'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('snapshot', sa.Column('date_created', sa.DateTime(), nullable=False))


def downgrade():
    op.drop_column('snapshot', 'date_created')
