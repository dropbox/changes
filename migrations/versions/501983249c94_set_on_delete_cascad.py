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
    op.drop_constraint('patch_change_id_fkey', 'patch')
    op.create_foreign_key('patch_change_id_fkey', 'patch', 'change', ['change_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('patch_project_id_fkey', 'patch')
    op.create_foreign_key('patch_project_id_fkey', 'patch', 'project', ['project_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('patch_repository_id_fkey', 'patch')
    op.create_foreign_key('patch_repository_id_fkey', 'patch', 'repository', ['repository_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass
