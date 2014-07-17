"""Adjust Command schema

Revision ID: 4768ba7627ac
Revises: 3f6a69c14037
Create Date: 2014-07-17 14:32:47.347947

"""

# revision identifiers, used by Alembic.
revision = '4768ba7627ac'
down_revision = '3f6a69c14037'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('command', sa.Column('order', sa.Integer(), nullable=False,
                                       server_default='0'))
    op.alter_column('command', 'return_code', existing_type=sa.INTEGER(),
                    nullable=True)


def downgrade():
    op.alter_column('command', 'return_code', existing_type=sa.INTEGER(),
                    nullable=False)
    op.drop_column('command', 'order')
