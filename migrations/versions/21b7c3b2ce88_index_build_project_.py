"""Index Build.project_id,patch_id,date_created

Revision ID: 21b7c3b2ce88
Revises: 4134b4818694
Create Date: 2013-12-03 16:19:11.794912

"""

# revision identifiers, used by Alembic.
revision = '21b7c3b2ce88'
down_revision = '4134b4818694'

from alembic import op


def upgrade():
    op.create_index('idx_build_project_patch_date', 'build', ['project_id', 'patch_id', 'date_created'])


def downgrade():
    pass
