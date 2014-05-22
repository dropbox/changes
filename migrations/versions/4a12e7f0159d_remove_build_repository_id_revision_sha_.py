"""Remove Build.{repository_id,revision_sha,patch_id}

Revision ID: 4a12e7f0159d
Revises: 1b2fa9c97090
Create Date: 2014-05-15 12:12:19.106724

"""

# revision identifiers, used by Alembic.
revision = '4a12e7f0159d'
down_revision = '1b2fa9c97090'

from alembic import op


def upgrade():
    op.drop_column('build', 'revision_sha')
    op.drop_column('build', 'repository_id')
    op.drop_column('build', 'patch_id')


def downgrade():
    raise NotImplementedError
