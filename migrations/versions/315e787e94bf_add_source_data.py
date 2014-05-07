"""Add Source.data

Revision ID: 315e787e94bf
Revises: 3f289637f530
Create Date: 2014-05-06 18:25:11.223951

"""

# revision identifiers, used by Alembic.
revision = '315e787e94bf'
down_revision = '3f289637f530'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('source', sa.Column('data', sa.JSONEncodedDict(), nullable=True))


def downgrade():
    op.drop_column('source', 'data')
