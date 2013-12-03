"""Index Build.project_id,date_created

Revision ID: f2c8d15416b
Revises: 152c9c780e
Create Date: 2013-12-03 15:54:09.488066

"""

# revision identifiers, used by Alembic.
revision = 'f2c8d15416b'
down_revision = '152c9c780e'

from alembic import op


def upgrade():
    op.create_index('idx_build_project_date', 'build', ['project_id', 'date_created'])


def downgrade():
    pass
