"""Rename BuildPlan -> JobPlan

Revision ID: 6483270c001
Revises: 4f955feb6d07
Create Date: 2013-12-25 23:37:07.896471

"""

# revision identifiers, used by Alembic.
revision = '6483270c001'
down_revision = '4f955feb6d07'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE buildplan RENAME TO jobplan')


def downgrade():
    op.execute('ALTER TABLE jobplan RENAME TO buildplan')
