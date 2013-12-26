"""AggregateTest*.build_id => job_id

Revision ID: 37244bf4e3f5
Revises: 57e24a9f2290
Create Date: 2013-12-26 01:24:37.395827

"""

# revision identifiers, used by Alembic.
revision = '37244bf4e3f5'
down_revision = '57e24a9f2290'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE aggtestsuite RENAME COLUMN first_build_id to first_job_id')
    op.execute('ALTER TABLE aggtestsuite RENAME COLUMN last_build_id to last_job_id')

    op.execute('ALTER TABLE aggtestgroup RENAME COLUMN first_build_id to first_job_id')
    op.execute('ALTER TABLE aggtestgroup RENAME COLUMN last_build_id to last_job_id')


def downgrade():
    op.execute('ALTER TABLE aggtestsuite RENAME COLUMN first_job_id to first_build_id')
    op.execute('ALTER TABLE aggtestsuite RENAME COLUMN last_job_id to last_build_id')

    op.execute('ALTER TABLE aggtestgroup RENAME COLUMN first_job_id to first_build_id')
    op.execute('ALTER TABLE aggtestgroup RENAME COLUMN last_job_id to last_build_id')
