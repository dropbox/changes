"""Index JobPhase

Revision ID: 139e272152de
Revises: 2f4637448764
Create Date: 2014-01-02 22:03:22.957636

"""

# revision identifiers, used by Alembic.
revision = '139e272152de'
down_revision = '2f4637448764'

from alembic import op


def upgrade():
    op.create_index('idx_jobphase_job_id', 'jobphase', ['job_id'])
    op.create_index('idx_jobphase_project_id', 'jobphase', ['project_id'])
    op.create_index('idx_jobphase_repository_id', 'jobphase', ['repository_id'])


def downgrade():
    op.drop_index('idx_jobphase_job_id', 'jobphase')
    op.drop_index('idx_jobphase_project_id', 'jobphase')
    op.drop_index('idx_jobphase_repository_id', 'jobphase')
