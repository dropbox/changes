"""change commands.env to text

Revision ID: 8550c7394f4
Revises: 5844fbc9d9e4
Create Date: 2015-06-15 13:42:13.990095

"""

# revision identifiers, used by Alembic.
revision = '8550c7394f4'
down_revision = '5844fbc9d9e4'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('command', 'env', type_ = sa.types.Text())


def downgrade():
    op.alter_column('command', 'env', type_ = sa.types.String(length=2048))

