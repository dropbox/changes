"""Remove test suite

Revision ID: 30b9f619c3b2
Revises: 3b55ff8856f5
Create Date: 2014-05-09 14:36:41.548924

"""

# revision identifiers, used by Alembic.
revision = '30b9f619c3b2'
down_revision = '3b55ff8856f5'

from alembic import op


def upgrade():
    op.create_unique_constraint('unq_test_name', 'test', ['job_id', 'label_sha'])
    op.drop_column('test', 'suite_id')

    op.drop_table('testsuite')


def downgrade():
    raise NotImplementedError
