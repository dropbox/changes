"""Add Artifact

Revision ID: 4e68c2a3d269
Revises: 586238e1375a
Create Date: 2014-02-06 10:24:04.343490

"""

# revision identifiers, used by Alembic.
revision = '4e68c2a3d269'
down_revision = '586238e1375a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'artifact',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('job_id', sa.GUID(), nullable=False),
        sa.Column('step_id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.Column('data', sa.JSONEncodedDict(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['job.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['step_id'], ['jobstep.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('step_id', 'name', name='unq_artifact_name'),
    )


def downgrade():
    op.drop_table('artifact')
