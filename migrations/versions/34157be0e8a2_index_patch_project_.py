"""Index Patch.project_id

Revision ID: 34157be0e8a2
Revises: f8ed1f99eb1
Create Date: 2014-01-02 21:59:37.076886

"""

# revision identifiers, used by Alembic.
revision = '34157be0e8a2'
down_revision = 'f8ed1f99eb1'

from alembic import op


def upgrade():
    op.create_index('idx_patch_project_id', 'patch', ['project_id'])


def downgrade():
    op.drop_index('idx_patch_project_id', 'patch')
