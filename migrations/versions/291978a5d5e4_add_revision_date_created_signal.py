"""add revision date created signal

Revision ID: 291978a5d5e4
Revises: 17c884f6f57c
Create Date: 2015-07-31 14:17:01.337179

"""

# revision identifiers, used by Alembic.
revision = '291978a5d5e4'
down_revision = '17c884f6f57c'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('revision', sa.Column('date_created_signal', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('revision', 'date_created_signal')
