"""Index Job(project_id, status, date_created) where patch_id IS NULL

Revision ID: 3042d0ca43bf
Revises: 3a3366fb7822
Create Date: 2014-01-03 15:24:39.947813

"""

# revision identifiers, used by Alembic.
revision = '3042d0ca43bf'
down_revision = '3a3366fb7822'

from alembic import op


def upgrade():
    op.execute('CREATE INDEX idx_job_previous_runs ON job (project_id, status, date_created) WHERE patch_id IS NULL')


def downgrade():
    op.drop_index('idx_job_previous_runs', 'job')
