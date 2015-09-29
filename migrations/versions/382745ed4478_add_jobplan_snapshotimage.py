"""add jobplan snapshotimage

Revision ID: 382745ed4478
Revises: 3e85891e90bb
Create Date: 2015-09-25 10:20:05.963135

"""

# revision identifiers, used by Alembic.
revision = '382745ed4478'
down_revision = '3e85891e90bb'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('jobplan', sa.Column('snapshot_image_id', sa.GUID(),
        sa.ForeignKey('snapshot_image.id', ondelete="RESTRICT"), nullable=True))


def downgrade():
    op.drop_column('jobplan', 'snapshot_image_id')
