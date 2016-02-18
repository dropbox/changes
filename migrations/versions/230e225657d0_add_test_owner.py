"""add_test_owner

Revision ID: 230e225657d0
Revises: 290a71847cd7
Create Date: 2016-02-18 00:14:58.856828

"""

# revision identifiers, used by Alembic.
revision = '230e225657d0'
down_revision = '290a71847cd7'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('test', sa.Column('owner', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('test', 'owner')
