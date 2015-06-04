"""Add column flakyteststat.first_run

Revision ID: 18c150792a21
Revises: 3bc4c6853367
Create Date: 2015-06-03 18:29:05.131373

"""

# revision identifiers, used by Alembic.
revision = '18c150792a21'
down_revision = '3bc4c6853367'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('flakyteststat', sa.Column('first_run', sa.Date(), nullable=True))


def downgrade():
    op.drop_column('flakyteststat', 'first_run')
