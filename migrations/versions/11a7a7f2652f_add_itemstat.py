"""Add ItemStat

Revision ID: 11a7a7f2652f
Revises: 4276d58dd1e6
Create Date: 2014-03-13 13:33:32.840399

"""

# revision identifiers, used by Alembic.
revision = '11a7a7f2652f'
down_revision = '4276d58dd1e6'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'itemstat',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('item_id', sa.GUID(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('value', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('item_id', 'name', name='unq_itemstat_name')
    )


def downgrade():
    op.drop_table('itemstat')
