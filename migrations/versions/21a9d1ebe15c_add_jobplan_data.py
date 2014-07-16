"""Add JobPlan.data

Revision ID: 21a9d1ebe15c
Revises: 19b8969073ab
Create Date: 2014-07-15 17:30:50.899914

"""

# revision identifiers, used by Alembic.
revision = '21a9d1ebe15c'
down_revision = '19b8969073ab'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('jobplan', sa.Column('data', sa.JSONEncodedDict(), nullable=True))


def downgrade():
    op.drop_column('jobplan', 'data')
