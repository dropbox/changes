"""Add Project.status

Revision ID: 2596f21c6f58
Revises: 4e68c2a3d269
Create Date: 2014-02-18 17:34:59.432346

"""

# revision identifiers, used by Alembic.
revision = '2596f21c6f58'
down_revision = '4e68c2a3d269'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('project', sa.Column('status', sa.Enum(), server_default='1', nullable=True))


def downgrade():
    op.drop_column('project', 'status')
