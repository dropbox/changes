"""add rerun count to tests

Revision ID: bb141e41aab
Revises: f8f72eecc7f
Create Date: 2014-03-28 13:57:17.364930

"""

# revision identifiers, used by Alembic.
revision = 'bb141e41aab'
down_revision = 'f8f72eecc7f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column(u'test', sa.Column('reruns', sa.INTEGER(), nullable=True))


def downgrade():
    op.drop_column(u'test', 'reruns')
