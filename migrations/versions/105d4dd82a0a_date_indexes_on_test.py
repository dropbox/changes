"""Date indexes on TestGroup

Revision ID: 105d4dd82a0a
Revises: 2d9df8a3103c
Create Date: 2013-11-19 12:24:02.607191

"""

# revision identifiers, used by Alembic.
revision = '105d4dd82a0a'
down_revision = '2d9df8a3103c'

from alembic import op


def upgrade():
    op.create_index('idx_testgroup_project_date', 'testgroup', ['project_id', 'date_created'])


def downgrade():
    pass
