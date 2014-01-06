"""Index Source.patch_id

Revision ID: 5508859bed73
Revises: 26f665189ca0
Create Date: 2014-01-06 11:14:19.109932

"""

# revision identifiers, used by Alembic.
revision = '5508859bed73'
down_revision = '26f665189ca0'

from alembic import op


def upgrade():
    op.create_index('idx_source_patch_id', 'source', ['patch_id'])


def downgrade():
    op.drop_index('idx_source_patch_id', 'source')
