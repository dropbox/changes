"""Unique constraint on Command

Revision ID: 19168fe64c41
Revises: 4768ba7627ac
Create Date: 2014-07-17 14:42:59.309732

"""

# revision identifiers, used by Alembic.
revision = '19168fe64c41'
down_revision = '4768ba7627ac'

from alembic import op


def upgrade():
    op.create_unique_constraint('unq_command_order', 'command', ['jobstep_id', 'order'])


def downgrade():
    op.drop_constraint('unq_command_order', 'command')
