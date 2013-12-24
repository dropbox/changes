"""Set ON DELETE CASCADE on BuildPhase.*

Revision ID: 469bba60eb50
Revises: 250341e605b7
Create Date: 2013-12-23 16:01:52.586436

"""

# revision identifiers, used by Alembic.
revision = '469bba60eb50'
down_revision = '250341e605b7'

from alembic import op


def upgrade():
    op.drop_constraint('buildphase_build_id_fkey', 'buildphase')
    op.create_foreign_key('buildphase_build_id_fkey', 'buildphase', 'build', ['build_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('buildphase_project_id_fkey', 'buildphase')
    op.create_foreign_key('buildphase_project_id_fkey', 'buildphase', 'project', ['project_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('buildphase_repository_id_fkey', 'buildphase')
    op.create_foreign_key('buildphase_repository_id_fkey', 'buildphase', 'repository', ['repository_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass
