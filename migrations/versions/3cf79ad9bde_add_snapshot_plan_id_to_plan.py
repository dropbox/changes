"""add_snapshot_plan_id_to_plan

Revision ID: 3cf79ad9bde
Revises: 26fa678dcc64
Create Date: 2015-07-08 10:24:29.696113

"""

# revision identifiers, used by Alembic.
revision = '3cf79ad9bde'
down_revision = '26fa678dcc64'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('plan', sa.Column('snapshot_plan_id', sa.GUID(), nullable=True))
    op.create_foreign_key('plan_snapshot_plan_id_fkey', 'plan', 'plan', ['snapshot_plan_id'], ['id'], ondelete='SET NULL')


def downgrade():
    op.drop_constraint('plan_snapshot_plan_id_fkey', 'plan')
    op.drop_column('plan', 'snapshot_plan_id')
