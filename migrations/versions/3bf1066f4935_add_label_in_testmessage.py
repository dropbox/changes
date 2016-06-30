"""Add label in testmessage

Revision ID: 3bf1066f4935
Revises: 51775a13339d
Create Date: 2016-06-30 14:12:07.405213

"""

# revision identifiers, used by Alembic.
revision = '3bf1066f4935'
down_revision = '51775a13339d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('testmessage', sa.Column('label', sa.Text(), nullable=True))
    testmessage = sa.table('testmessage', sa.column('label'))
    op.execute(testmessage.update().values(label='test-message'))
    op.alter_column('testmessage', 'label', nullable=False)


def downgrade():
    op.drop_column('testmessage', 'label')
