"""Update Source constraints

Revision ID: 2f3ba1e84a6f
Revises: cb99fdfb903
Create Date: 2013-12-23 14:46:38.140915

"""

# revision identifiers, used by Alembic.
revision = '2f3ba1e84a6f'
down_revision = 'cb99fdfb903'

from alembic import op


def upgrade():
    op.execute('CREATE UNIQUE INDEX unq_source_revision ON source (repository_id, revision_sha) WHERE patch_id IS NULL')
    op.execute('CREATE UNIQUE INDEX unq_source_patch_id ON source (patch_id) WHERE patch_id IS NOT NULL')


def downgrade():
    op.drop_constraint('unq_source_revision', 'source')
    op.drop_constraint('unq_source_patch_id', 'source')
