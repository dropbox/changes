"""Set ON DELETE CASCADE on Change.*

Revision ID: 54a5c0c8793b
Revises: 4289d4c9dac6
Create Date: 2013-12-23 16:36:32.007578

"""

# revision identifiers, used by Alembic.
revision = '54a5c0c8793b'
down_revision = '4289d4c9dac6'

from alembic import op


def upgrade():
    op.drop_constraint('change_project_id_fkey', 'change')
    op.create_foreign_key('change_project_id_fkey', 'change', 'project', ['project_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('change_author_id_fkey', 'change')
    op.create_foreign_key('change_author_id_fkey', 'change', 'author', ['author_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('change_repository_id_fkey', 'change')
    op.create_foreign_key('change_repository_id_fkey', 'change', 'repository', ['repository_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass
