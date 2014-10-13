"""Add Plan.avg_build_time

Revision ID: 4c3f2a63b7a7
Revises: 4cd8cf6a0894
Create Date: 2014-10-09 15:21:09.463279

"""

# revision identifiers, used by Alembic.
revision = '4c3f2a63b7a7'
down_revision = '4cd8cf6a0894'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('plan', sa.Column('avg_build_time', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('plan', 'avg_build_time')
