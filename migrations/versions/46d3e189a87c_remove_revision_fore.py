"""Remove revision foreignkeys

Revision ID: 46d3e189a87c
Revises: cd427091f31
Create Date: 2013-09-27 15:24:21.691512

"""

# revision identifiers, used by Alembic.
revision = '46d3e189a87c'
down_revision = 'cd427091f31'

from alembic import op


def upgrade():
    op.drop_constraint(
        'build_repository_id_fkey', 'build', 'foreignkey',
    )
    op.drop_constraint(
        'change_repository_id_fkey', 'change', 'foreignkey',
    )
    op.drop_constraint(
        'change_repository_id_fkey1', 'change', 'foreignkey',
    )


def downgrade():
    op.create_foreign_key(
        'build_repository_id_fkey', 'build', 'revision',
        ['repository_id', 'parent_revision_sha'],
        ['revision.repository_id', 'revision.sha'],
    )
    op.create_foreign_key(
        'change_repository_id_fkey', 'change', 'revision',
        ['repository_id', 'parent_revision_sha'],
        ['revision.repository_id', 'revision.sha'],
    )
    op.create_foreign_key(
        'change_repository_id_fkey1', 'change', 'revision',
        ['repository_id', 'revision_sha'],
        ['revision.repository_id', 'revision.sha'],
    )
