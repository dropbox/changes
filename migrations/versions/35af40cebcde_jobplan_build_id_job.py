"""JobPlan.build_id => job_id

Revision ID: 35af40cebcde
Revises: 2b4219a6cf46
Create Date: 2013-12-26 00:18:58.945167

"""

# revision identifiers, used by Alembic.
revision = '35af40cebcde'
down_revision = '2b4219a6cf46'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE jobplan RENAME COLUMN build_id TO job_id')


def downgrade():
    op.execute('ALTER TABLE jobplan RENAME COLUMN job_id TO build_id')
