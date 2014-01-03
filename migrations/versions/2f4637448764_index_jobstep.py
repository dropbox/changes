"""Index JobStep

Revision ID: 2f4637448764
Revises: 34157be0e8a2
Create Date: 2014-01-02 22:01:33.969503

"""

# revision identifiers, used by Alembic.
revision = '2f4637448764'
down_revision = '34157be0e8a2'

from alembic import op


def upgrade():
    op.create_index('idx_jobstep_job_id', 'jobstep', ['job_id'])
    op.create_index('idx_jobstep_project_id', 'jobstep', ['project_id'])
    op.create_index('idx_jobstep_phase_id', 'jobstep', ['phase_id'])
    op.create_index('idx_jobstep_repository_id', 'jobstep', ['repository_id'])
    op.create_index('idx_jobstep_node_id', 'jobstep', ['node_id'])


def downgrade():
    op.drop_index('idx_jobstep_job_id', 'jobstep')
    op.drop_index('idx_jobstep_project_id', 'jobstep')
    op.drop_index('idx_jobstep_phase_id', 'jobstep')
    op.drop_index('idx_jobstep_repository_id', 'jobstep')
    op.drop_index('idx_jobstep_node_id', 'jobstep')
