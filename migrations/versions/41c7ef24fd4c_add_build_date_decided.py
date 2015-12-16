"""add Build.date_decided

Revision ID: 41c7ef24fd4c
Revises: 3961ccb5d884
Create Date: 2015-12-16 13:27:24.838841

"""

# revision identifiers, used by Alembic.
revision = '41c7ef24fd4c'
down_revision = '3961ccb5d884'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('build', sa.Column('date_decided', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('build', 'date_decided')
