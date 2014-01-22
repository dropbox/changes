"""Add Task.data

Revision ID: 97786e74292
Revises: 4ae598236ef1
Create Date: 2014-01-21 17:40:42.013002

"""

# revision identifiers, used by Alembic.
revision = '97786e74292'
down_revision = '4ae598236ef1'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('task', sa.Column('data', sa.JSONEncodedDict(), nullable=True))


def downgrade():
    op.drop_column('task', 'data')
