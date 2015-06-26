"""add cached_snapshot_image table

Revision ID: 26fa678dcc64
Revises: 8550c7394f4
Create Date: 2015-06-26 09:21:03.600713

"""

# revision identifiers, used by Alembic.
revision = '26fa678dcc64'
down_revision = '8550c7394f4'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'cached_snapshot_image',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('expiration_date', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['id'], ['snapshot_image.id'], ondelete='CASCADE'),
    )

    # We do a lot of comparison queries on the expiration date so
    # we require an index here for efficient operations
    op.create_index('idx_cached_snapshot_image_expiration_date', 'cached_snapshot_image', ['expiration_date'])


def downgrade():
    op.drop_index('idx_cached_snapshot_image_expiration_date', 'cached_snapshot_image')
    op.drop_table('cached_snapshot_image')
