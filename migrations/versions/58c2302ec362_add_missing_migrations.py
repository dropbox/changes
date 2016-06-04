"""add missing migrations

Revision ID: 58c2302ec362
Revises: 230e225657d0
Create Date: 2016-06-01 21:25:54.451631

"""

# revision identifiers, used by Alembic.
revision = '58c2302ec362'
down_revision = '230e225657d0'

from alembic import op


def upgrade():
    op.create_index('idx_artifact_job_id', 'artifact', ['job_id'])
    # This index has never been used by any query in the past
    op.create_index('idx_artifact_project_id', 'artifact', ['project_id'])
    op.create_index('idx_build_latest', 'build', ['project_id', 'status', 'date_created'])
    op.create_index('idx_filecoverage_step_id', 'filecoverage', ['step_id'])
    op.create_index('idx_job_source_date', 'job', ['source_id', 'status', 'date_created'])
    op.create_index('idx_jobstep_project_date', 'jobstep', ['project_id', 'date_created'])
    op.create_index('idx_logchunk_date_created', 'logchunk', ['date_created'])
    # This index has never been used by any query in the past
    op.create_index('idx_logsource_date_created', 'logsource', ['date_created'])
    op.create_index('idx_logsource_step_id', 'logsource', ['step_id'])
    op.execute('CREATE INDEX idx_source_commit ON source USING btree (id) WHERE ((patch_id IS NULL) AND (revision_sha IS NOT NULL))')
    op.create_index('idx_task_date_created', 'task', ['date_created'])
    op.create_index('idx_test_date_created', 'test', ['date_created'])
    op.create_index('idx_test_project_key_date', 'test', ['project_id', 'label_sha', 'date_created'])
    op.create_index('revision_author_id', 'revision', ['author_id'])


def downgrade():
    op.drop_index('idx_artifact_job_id', 'artifact')
    op.drop_index('idx_artifact_project_id', 'artifact')
    op.drop_index('idx_build_latest', 'build')
    op.drop_index('idx_filecoverage_step_id', 'filecoverage')
    op.drop_index('idx_job_source_date', 'job')
    op.drop_index('idx_jobstep_project_date', 'jobstep')
    op.drop_index('idx_logchunk_date_created', 'logchunk')
    op.drop_index('idx_logsource_date_created', 'logsource')
    op.drop_index('idx_logsource_step_id', 'logsource')
    op.drop_index('idx_source_commit', 'source')
    op.drop_index('idx_task_date_created', 'task')
    op.drop_index('idx_test_date_created', 'test')
    op.drop_index('idx_test_project_key_date', 'test')
    op.drop_index('revision_author_id', 'revision')
