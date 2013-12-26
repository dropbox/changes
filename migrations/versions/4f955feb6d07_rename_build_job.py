"""Rename Build -> Job

Revision ID: 4f955feb6d07
Revises: 554f414d4c46
Create Date: 2013-12-25 23:17:26.666301

"""

# revision identifiers, used by Alembic.
revision = '4f955feb6d07'
down_revision = '554f414d4c46'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE build RENAME TO job')


def downgrade():
    op.execute('ALTER TABLE job RENAME TO build')
