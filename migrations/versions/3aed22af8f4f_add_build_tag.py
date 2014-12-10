"""Add Build.tags

Revision ID: 3aed22af8f4f
Revises: 4e2d942b58b0
Create Date: 2014-12-01 12:38:25.867513

"""

# revision identifiers, used by Alembic.
revision = '3aed22af8f4f'
down_revision = '4e2d942b58b0'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.add_column('build', sa.Column('tags', postgresql.ARRAY(sa.String(length=16)), nullable=True))


def downgrade():
    op.drop_column('build', 'tags')
