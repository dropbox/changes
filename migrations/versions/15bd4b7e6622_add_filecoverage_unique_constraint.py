"""Add FileCoverage unique constraint

Revision ID: 15bd4b7e6622
Revises: 3d8177efcfe1
Create Date: 2014-05-09 11:06:50.845168

"""

# revision identifiers, used by Alembic.
revision = '15bd4b7e6622'
down_revision = '3d8177efcfe1'

from alembic import op


def upgrade():
    op.create_unique_constraint('unq_job_filname', 'filecoverage', ['job_id', 'filename'])


def downgrade():
    op.drop_constraint('unq_job_filname', 'filecoverage')
