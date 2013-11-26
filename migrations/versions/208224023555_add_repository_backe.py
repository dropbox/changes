"""Add Repository.backend

Revision ID: 208224023555
Revises: 1d1f467bdf3d
Create Date: 2013-11-25 15:12:30.867388

"""

# revision identifiers, used by Alembic.
revision = '208224023555'
down_revision = '1d1f467bdf3d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('repository', sa.Column('backend', sa.Enum(), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('repository', 'backend')
