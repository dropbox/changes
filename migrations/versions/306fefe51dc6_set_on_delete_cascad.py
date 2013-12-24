"""Set ON DELETE CASCADE on Project Plan m2m

Revision ID: 306fefe51dc6
Revises: 37e782a55ca6
Create Date: 2013-12-23 16:44:37.119363

"""

# revision identifiers, used by Alembic.
revision = '306fefe51dc6'
down_revision = '37e782a55ca6'

from alembic import op


def upgrade():
    op.drop_constraint('project_plan_plan_id_fkey', 'project_plan')
    op.create_foreign_key('project_plan_plan_id_fkey', 'project_plan', 'plan', ['plan_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('project_plan_project_id_fkey', 'project_plan')
    op.create_foreign_key('project_plan_project_id_fkey', 'project_plan', 'project', ['project_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass
