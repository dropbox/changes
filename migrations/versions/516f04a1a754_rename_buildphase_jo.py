"""Rename BuildPhase -> JobPhase

Revision ID: 516f04a1a754
Revises: 6483270c001
Create Date: 2013-12-25 23:40:42.892745

"""

# revision identifiers, used by Alembic.
revision = '516f04a1a754'
down_revision = '6483270c001'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE buildphase RENAME TO jobphase')


def downgrade():
    op.execute('ALTER TABLE jobphase RENAME TO buildphase')
