"""Add FileCoverage.step_id

Revision ID: 3d8177efcfe1
Revises: 3df65ebfa27e
Create Date: 2014-05-08 11:19:04.251803

"""

# revision identifiers, used by Alembic.
revision = '3d8177efcfe1'
down_revision = '3df65ebfa27e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('filecoverage', sa.Column('step_id', sa.GUID(), nullable=True))


def downgrade():
    op.drop_column('filecoverage', 'step_id')
