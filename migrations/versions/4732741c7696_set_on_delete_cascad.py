"""Set ON DELETE CASCADE on BuildFamily.*

Revision ID: 4732741c7696
Revises: 102eea94977e
Create Date: 2013-12-23 16:05:01.655149

"""

# revision identifiers, used by Alembic.
revision = '4732741c7696'
down_revision = '102eea94977e'

from alembic import op


def upgrade():
    op.drop_constraint('buildfamily_author_id_fkey', 'buildfamily')
    op.create_foreign_key('buildfamily_author_id_fkey', 'buildfamily', 'author', ['author_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('buildfamily_patch_id_fkey', 'buildfamily')
    op.create_foreign_key('buildfamily_patch_id_fkey', 'buildfamily', 'patch', ['patch_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('buildfamily_project_id_fkey', 'buildfamily')
    op.create_foreign_key('buildfamily_project_id_fkey', 'buildfamily', 'project', ['project_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('buildfamily_repository_id_fkey', 'buildfamily')
    op.create_foreign_key('buildfamily_repository_id_fkey', 'buildfamily', 'repository', ['repository_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass
