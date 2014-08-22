"""Add SnapshotImage.status

Revision ID: 57e4a0553903
Revises: 30c86cc72856
Create Date: 2014-08-21 23:03:23.553069

"""

# revision identifiers, used by Alembic.
revision = '57e4a0553903'
down_revision = '30c86cc72856'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('snapshot_image', sa.Column('status', sa.Enum(), server_default='0', nullable=False))


def downgrade():
    op.drop_column('snapshot_image', 'status')
