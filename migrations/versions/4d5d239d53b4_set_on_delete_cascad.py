"""Set ON DELETE CASCADE on TestSuite.*

Revision ID: 4d5d239d53b4
Revises: 501983249c94
Create Date: 2013-12-23 16:14:08.812850

"""

# revision identifiers, used by Alembic.
revision = '4d5d239d53b4'
down_revision = '501983249c94'

from alembic import op


def upgrade():
    op.drop_constraint('testsuite_project_id_fkey', 'testsuite')
    op.create_foreign_key('testsuite_project_id_fkey', 'testsuite', 'project', ['project_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('testsuite_build_id_fkey', 'testsuite')
    op.create_foreign_key('testsuite_build_id_fkey', 'testsuite', 'build', ['build_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass
