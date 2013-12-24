"""Set ON DELETE CASCADE on BuildPlan.*

Revision ID: 250341e605b7
Revises: 1eefd7dfedb2
Create Date: 2013-12-23 15:59:44.408248

"""

# revision identifiers, used by Alembic.
revision = '250341e605b7'
down_revision = '1eefd7dfedb2'

from alembic import op


def upgrade():
    op.drop_constraint('buildplan_build_id_fkey', 'buildplan')
    op.create_foreign_key('buildplan_build_id_fkey', 'buildplan', 'build', ['build_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('buildplan_family_id_fkey', 'buildplan')
    op.create_foreign_key('buildplan_family_id_fkey', 'buildplan', 'buildfamily', ['family_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('buildplan_plan_id_fkey', 'buildplan')
    op.create_foreign_key('buildplan_plan_id_fkey', 'buildplan', 'plan', ['plan_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('buildplan_project_id_fkey', 'buildplan')
    op.create_foreign_key('buildplan_project_id_fkey', 'buildplan', 'project', ['project_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass
