"""Add Build.priority

Revision ID: 36cbde703cc0
Revises: fe743605e1a
Create Date: 2014-10-06 10:10:14.729720

"""

# revision identifiers, used by Alembic.
revision = '36cbde703cc0'
down_revision = '2c6662281b66'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('build', sa.Column('priority', sa.Enum(), server_default='0', nullable=False))


def downgrade():
    op.drop_column('build', 'priority')
