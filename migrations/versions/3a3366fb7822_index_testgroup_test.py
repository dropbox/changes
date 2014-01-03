"""Index testgroup_test.test_id

Revision ID: 3a3366fb7822
Revises: 139e272152de
Create Date: 2014-01-02 22:20:55.132222

"""

# revision identifiers, used by Alembic.
revision = '3a3366fb7822'
down_revision = '139e272152de'

from alembic import op


def upgrade():
    op.create_index('idx_testgroup_test_test_id', 'testgroup_test', ['test_id'])


def downgrade():
    op.drop_index('idx_testgroup_test_test_id', 'testgroup_test')
