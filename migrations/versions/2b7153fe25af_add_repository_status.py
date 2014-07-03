"""Add Repository.status

Revision ID: 2b7153fe25af
Revises: 3b22c1663664
Create Date: 2014-07-03 12:18:06.616440

"""

# revision identifiers, used by Alembic.
revision = '2b7153fe25af'
down_revision = '3b22c1663664'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('repository', sa.Column('status', sa.Enum(), server_default='1', nullable=False))


def downgrade():
    op.drop_column('repository', 'status')
