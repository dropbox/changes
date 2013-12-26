"""Rename BuildStep -> JobStep

Revision ID: 42e9d35a4098
Revises: 516f04a1a754
Create Date: 2013-12-25 23:44:30.776610

"""

# revision identifiers, used by Alembic.
revision = '42e9d35a4098'
down_revision = '516f04a1a754'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE buildstep RENAME TO jobstep')


def downgrade():
    op.execute('ALTER TABLE jobstep RENAME TO buildstep')
