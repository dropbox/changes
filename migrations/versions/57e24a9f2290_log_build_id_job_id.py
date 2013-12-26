"""Log*.build_id => job_id

Revision ID: 57e24a9f2290
Revises: 35af40cebcde
Create Date: 2013-12-26 01:03:06.812123

"""

# revision identifiers, used by Alembic.
revision = '57e24a9f2290'
down_revision = '35af40cebcde'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE logsource RENAME COLUMN build_id TO job_id')
    op.execute('ALTER TABLE logchunk RENAME COLUMN build_id TO job_id')


def downgrade():
    op.execute('ALTER TABLE logsource RENAME COLUMN job_id TO build_id')
    op.execute('ALTER TABLE logchunk RENAME COLUMN job_id TO build_id')
