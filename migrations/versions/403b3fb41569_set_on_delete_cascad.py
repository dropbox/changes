"""Set ON DELETE CASCADE on Build.*

Revision ID: 403b3fb41569
Revises: 4732741c7696
Create Date: 2013-12-23 16:07:02.202873

"""

# revision identifiers, used by Alembic.
revision = '403b3fb41569'
down_revision = '4732741c7696'

from alembic import op


def upgrade():
    op.drop_constraint('build_author_id_fkey', 'build')
    op.create_foreign_key('build_author_id_fkey', 'build', 'author', ['author_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('build_change_id_fkey', 'build')
    op.create_foreign_key('build_change_id_fkey', 'build', 'change', ['change_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('build_patch_id_fkey', 'build')
    op.create_foreign_key('build_patch_id_fkey', 'build', 'patch', ['patch_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('build_project_id_fkey', 'build')
    op.create_foreign_key('build_project_id_fkey', 'build', 'project', ['project_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('build_repository_id_fkey', 'build')
    op.create_foreign_key('build_repository_id_fkey', 'build', 'repository', ['repository_id'], ['id'], ondelete='CASCADE')

    # add missing constraints
    op.create_foreign_key('build_family_id_fkey', 'build', 'buildfamily', ['family_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('build_source_id_fkey', 'build', 'source', ['source_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('build_parent_id_fkey', 'build', 'build', ['parent_id'], ['id'], ondelete='CASCADE')


def downgrade():
    op.drop_constraint('build_family_id_fkey', 'build')
    op.drop_constraint('build_source_id_fkey', 'build')
    op.drop_constraint('build_parent_id_fkey', 'build')
