"""Add cascade to FileCoverage

Revision ID: 21c9439330f
Revises: 1f5caa34d9c2
Create Date: 2014-04-01 15:29:26.765288

"""

# revision identifiers, used by Alembic.
revision = '21c9439330f'
down_revision = '1f5caa34d9c2'

from alembic import op


def upgrade():
    op.create_index('idx_filecoverage_job_id', 'filecoverage', ['job_id'])
    op.create_index('idx_filecoverage_project_id', 'filecoverage', ['project_id'])

    op.drop_constraint('filecoverage_build_id_fkey', 'filecoverage')
    op.create_foreign_key('filecoverage_job_id_fkey', 'filecoverage', 'job', ['job_id'], ['id'], ondelete='CASCADE')

    op.create_foreign_key('filecoverage_project_id_fkey', 'filecoverage', 'project', ['project_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass
