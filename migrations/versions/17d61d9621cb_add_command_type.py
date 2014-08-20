"""Add Command.type

Revision ID: 17d61d9621cb
Revises: 46a612aff7d3
Create Date: 2014-08-18 13:25:39.609575

"""

# revision identifiers, used by Alembic.
revision = '17d61d9621cb'
down_revision = '46a612aff7d3'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('command', sa.Column('type', sa.Enum(), server_default='0', nullable=False))


def downgrade():
    op.drop_column('command', 'type')
