"""Set ON DELETE CASCADE on AggregateTestGroup.*

Revision ID: 4289d4c9dac6
Revises: 1caf0d25843b
Create Date: 2013-12-23 16:15:30.023843

"""

# revision identifiers, used by Alembic.
revision = '4289d4c9dac6'
down_revision = '1caf0d25843b'

from alembic import op


def upgrade():
    op.drop_constraint('aggtestgroup_project_id_fkey', 'aggtestgroup')
    op.create_foreign_key('aggtestgroup_project_id_fkey', 'aggtestgroup', 'project', ['project_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('aggtestgroup_suite_id_fkey', 'aggtestgroup')
    op.create_foreign_key('aggtestgroup_suite_id_fkey', 'aggtestgroup', 'aggtestsuite', ['suite_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('aggtestgroup_parent_id_fkey', 'aggtestgroup')
    op.create_foreign_key('aggtestgroup_parent_id_fkey', 'aggtestgroup', 'aggtestgroup', ['suite_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('aggtestgroup_first_build_id_fkey', 'aggtestgroup')
    op.create_foreign_key('aggtestgroup_first_build_id_fkey', 'aggtestgroup', 'build', ['first_build_id'], ['id'], ondelete='CASCADE')

    op.create_foreign_key('aggtestgroup_last_build_id_fkey', 'aggtestgroup', 'build', ['last_build_id'], ['id'], ondelete='CASCADE')


def downgrade():
    op.drop_constraint('aggtestgroup_last_build_id_fkey', 'aggtestgroup')
