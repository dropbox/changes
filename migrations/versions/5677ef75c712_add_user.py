"""Add User

Revision ID: 5677ef75c712
Revises: 45e1cfacfc7d
Create Date: 2014-01-15 11:06:25.217408

"""

# revision identifiers, used by Alembic.
revision = '5677ef75c712'
down_revision = '45e1cfacfc7d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'user',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('email', sa.String(length=128), nullable=False),
        sa.Column('is_admin', sa.Boolean(), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )


def downgrade():
    op.drop_table('user')
