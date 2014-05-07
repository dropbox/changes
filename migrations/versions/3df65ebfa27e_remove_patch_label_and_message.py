"""Remove Patch label and message

Revision ID: 3df65ebfa27e
Revises: 315e787e94bf
Create Date: 2014-05-06 18:41:16.245897

"""

# revision identifiers, used by Alembic.
revision = '3df65ebfa27e'
down_revision = '315e787e94bf'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_column('patch', 'message')
    op.drop_column('patch', 'label')


def downgrade():
    op.add_column('patch', sa.Column('label', sa.VARCHAR(length=64), nullable=False))
    op.add_column('patch', sa.Column('message', sa.TEXT(), nullable=True))
