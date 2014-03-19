"""Add Revision.branches

Revision ID: 36becb086fcb
Revises: 11a7a7f2652f
Create Date: 2014-03-18 17:48:37.484301

"""

# revision identifiers, used by Alembic.
revision = '36becb086fcb'
down_revision = '11a7a7f2652f'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.add_column('revision', sa.Column('branches', postgresql.ARRAY(sa.String(length=128)), nullable=True))


def downgrade():
    op.drop_column('revision', 'branches')
