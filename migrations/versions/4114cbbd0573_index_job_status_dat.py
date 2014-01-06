"""Index Job.{status,date_created}

Revision ID: 4114cbbd0573
Revises: 5508859bed73
Create Date: 2014-01-06 11:28:15.691391

"""

# revision identifiers, used by Alembic.
revision = '4114cbbd0573'
down_revision = '5508859bed73'

from alembic import op


def upgrade():
    op.create_index('idx_job_status_date_created', 'job', ['status', 'date_created'])


def downgrade():
    op.drop_index('idx_job_status_date_created', 'job')
