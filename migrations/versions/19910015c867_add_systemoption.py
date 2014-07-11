"""Add SystemOption

Revision ID: 19910015c867
Revises: 2b7153fe25af
Create Date: 2014-07-11 15:48:26.276042

"""

# revision identifiers, used by Alembic.
revision = '19910015c867'
down_revision = '2b7153fe25af'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'systemoption',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )


def downgrade():
    op.drop_table('systemoption')
