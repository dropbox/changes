"""Set ON DELETE CASCADE on Patch.*

Revision ID: 501983249c94
Revises: 403b3fb41569
Create Date: 2013-12-23 16:12:13.610366

"""

# revision identifiers, used by Alembic.
revision = '501983249c94'
down_revision = '403b3fb41569'

from alembic import op


def upgrade():
    op.drop_constraint('testsuite_project_id_fkey', 'testsuite')
    op.create_foreign_key('testsuite_project_id_fkey', 'testsuite', 'project', ['project_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('testsuite_build_id_fkey', 'testsuite')
    op.create_foreign_key('testsuite_build_id_fkey', 'testsuite', 'build', ['build_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass
