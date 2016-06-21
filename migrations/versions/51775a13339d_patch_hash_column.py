"""patch hash column

Revision ID: 51775a13339d
Revises: 016f138b2da8
Create Date: 2016-06-17 13:46:10.921685

"""

# revision identifiers, used by Alembic.
revision = '51775a13339d'
down_revision = '016f138b2da8'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('revision', sa.Column('patch_hash', sa.String(40), nullable=True))


def downgrade():
    op.drop_column('revision', 'patch_hash')
