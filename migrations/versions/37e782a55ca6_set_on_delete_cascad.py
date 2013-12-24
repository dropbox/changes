"""Set ON DELETE CASCADE on Project*

Revision ID: 37e782a55ca6
Revises: 218e84b10a0e
Create Date: 2013-12-23 16:41:27.462599

"""

# revision identifiers, used by Alembic.
revision = '37e782a55ca6'
down_revision = '218e84b10a0e'

from alembic import op


def upgrade():
    op.drop_constraint('project_repository_id_fkey', 'project')
    op.create_foreign_key('project_repository_id_fkey', 'project', 'repository', ['repository_id'], ['id'], ondelete='RESTRICT')

    op.drop_constraint('projectoption_project_id_fkey', 'projectoption')
    op.create_foreign_key('projectoption_project_id_fkey', 'projectoption', 'project', ['project_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass
