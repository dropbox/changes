"""Remove idx_testgroup_project_id

Revision ID: f8f72eecc7f
Revises: 1db7a1ab95db
Create Date: 2014-03-27 12:12:15.548413

"""

# revision identifiers, used by Alembic.
revision = 'f8f72eecc7f'
down_revision = '1db7a1ab95db'

from alembic import op


def upgrade():
    op.drop_index('idx_testgroup_project_id', 'testgroup')


def downgrade():
    op.create_index('idx_testgroup_project_id', 'testgroup', ['project_id'])
