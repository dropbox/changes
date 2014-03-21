"""Fix FileCoverage.project_id

Revision ID: 1db7a1ab95db
Revises: 36becb086fcb
Create Date: 2014-03-21 15:47:41.430619

"""

# revision identifiers, used by Alembic.
revision = '1db7a1ab95db'
down_revision = '36becb086fcb'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_column('filecoverage', 'project_id')
    op.add_column('filecoverage', sa.Column('project_id', sa.GUID(), nullable=False))


def downgrade():
    raise NotImplementedError
