"""Set ON DELETE CASCADE on BuildStep.*

Revision ID: 102eea94977e
Revises: 469bba60eb50
Create Date: 2013-12-23 16:01:57.926119

"""

# revision identifiers, used by Alembic.
revision = '102eea94977e'
down_revision = '469bba60eb50'

from alembic import op


def upgrade():
    op.drop_constraint('buildstep_build_id_fkey', 'buildstep')
    op.create_foreign_key('buildstep_build_id_fkey', 'buildstep', 'build', ['build_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('buildstep_node_id_fkey', 'buildstep')
    op.create_foreign_key('buildstep_node_id_fkey', 'buildstep', 'node', ['node_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('buildstep_phase_id_fkey', 'buildstep')
    op.create_foreign_key('buildstep_phase_id_fkey', 'buildstep', 'buildphase', ['phase_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('buildstep_project_id_fkey', 'buildstep')
    op.create_foreign_key('buildstep_project_id_fkey', 'buildstep', 'project', ['project_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('buildstep_repository_id_fkey', 'buildstep')
    op.create_foreign_key('buildstep_repository_id_fkey', 'buildstep', 'repository', ['repository_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass
