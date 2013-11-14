"""Add LogChunk unique constraint

Revision ID: 2d9df8a3103c
Revises: 393be9b08e4c
Create Date: 2013-11-13 17:12:48.662009

"""

# revision identifiers, used by Alembic.
revision = '2d9df8a3103c'
down_revision = '393be9b08e4c'

from alembic import op


def upgrade():
    op.create_unique_constraint('unq_logchunk_source_offset', 'logchunk', ['source_id', 'offset'])


def downgrade():
    op.drop_constraint('unq_logchunk_source_offset', 'logchunk')
