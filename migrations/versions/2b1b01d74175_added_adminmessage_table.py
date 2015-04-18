"""Added adminmessage table

Revision ID: 2b1b01d74175
Revises: 1cb3db431e29
Create Date: 2015-04-15 22:55:56.097518

"""

# revision identifiers, used by Alembic.
revision = '2b1b01d74175'
down_revision = '1cb3db431e29'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('adminmessage',
                    sa.Column('id', sa.GUID(), nullable=False),
                    sa.Column('user_id', sa.GUID(), nullable=True),
                    sa.Column('date_created', sa.DateTime(), nullable=True),
                    sa.Column('message', sa.Text(), nullable=True),
                    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
                    sa.PrimaryKeyConstraint('id'))


def downgrade():
    op.drop_table('adminmessage')
