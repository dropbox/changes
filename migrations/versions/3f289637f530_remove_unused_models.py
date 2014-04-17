"""Remove unused models

Revision ID: 3f289637f530
Revises: 4ba1dd8c3080
Create Date: 2014-04-17 11:08:50.963964

"""

# revision identifiers, used by Alembic.
revision = '3f289637f530'
down_revision = '4ba1dd8c3080'

from alembic import op


def upgrade():
    op.drop_table('aggtestgroup')
    op.drop_table('testgroup_test')
    op.drop_table('testgroup')
    op.drop_table('aggtestsuite')


def downgrade():
    raise NotImplementedError
