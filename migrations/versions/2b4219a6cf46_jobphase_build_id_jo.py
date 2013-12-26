"""JobPhase.build_id => job_id

Revision ID: 2b4219a6cf46
Revises: f26b6cb3c9c
Create Date: 2013-12-26 00:16:20.974336

"""

# revision identifiers, used by Alembic.
revision = '2b4219a6cf46'
down_revision = 'f26b6cb3c9c'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE jobphase RENAME COLUMN build_id TO job_id')


def downgrade():
    op.execute('ALTER TABLE jobphase RENAME COLUMN job_id TO build_id')
