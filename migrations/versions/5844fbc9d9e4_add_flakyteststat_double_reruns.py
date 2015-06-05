"""Add flakyteststat.double_reruns

Revision ID: 5844fbc9d9e4
Revises: 18c150792a21
Create Date: 2015-06-04 14:20:02.697048

"""

# revision identifiers, used by Alembic.
revision = '5844fbc9d9e4'
down_revision = '18c150792a21'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('flakyteststat', sa.Column('double_reruns', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('flakyteststat', 'double_reruns')
