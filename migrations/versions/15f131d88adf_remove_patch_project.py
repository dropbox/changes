"""Remove patch.project

Revision ID: 15f131d88adf
Revises: 1c5907e309f1
Create Date: 2014-06-10 14:36:35.068328

"""

# revision identifiers, used by Alembic.
revision = '15f131d88adf'
down_revision = '1c5907e309f1'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.drop_column('patch', 'project_id')


def downgrade():
    op.create_index('idx_patch_project_id', 'patch', ['project_id'], unique=False)
    op.add_column('patch', sa.Column('project_id', postgresql.UUID(), nullable=False))
