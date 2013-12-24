"""Set ON DELETE CASCADE on AggregateTestSuite.*

Revision ID: 1caf0d25843b
Revises: 4d5d239d53b4
Create Date: 2013-12-23 16:15:27.526777

"""

# revision identifiers, used by Alembic.
revision = '1caf0d25843b'
down_revision = '4d5d239d53b4'

from alembic import op


def upgrade():
    op.drop_constraint('aggtestsuite_project_id_fkey', 'aggtestsuite')
    op.create_foreign_key('aggtestsuite_project_id_fkey', 'aggtestsuite', 'project', ['project_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('aggtestsuite_first_build_id_fkey', 'aggtestsuite')
    op.create_foreign_key('aggtestsuite_first_build_id_fkey', 'aggtestsuite', 'build', ['first_build_id'], ['id'], ondelete='CASCADE')

    op.create_foreign_key('aggtestsuite_last_build_id_fkey', 'aggtestsuite', 'build', ['last_build_id'], ['id'], ondelete='CASCADE')


def downgrade():
    op.drop_constraint('aggtestsuite_last_build_id_fkey', 'aggtestsuite')
