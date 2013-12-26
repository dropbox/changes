"""Add Build/Job numbers

Revision ID: 25d63e09ea3b
Revises: 1ad857c78a0d
Create Date: 2013-12-26 02:36:58.663362

"""

# revision identifiers, used by Alembic.
revision = '25d63e09ea3b'
down_revision = '1ad857c78a0d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('build', sa.Column('number', sa.Integer(), nullable=True))
    op.add_column('job', sa.Column('number', sa.Integer(), nullable=True))
    op.create_unique_constraint('unq_build_number', 'build', ['project_id', 'number'])
    op.create_unique_constraint('unq_job_number', 'job', ['build_id', 'number'])


def downgrade():
    op.drop_column('build', 'number')
    op.drop_column('job', 'number')
    op.drop_constraint('unq_build_number', 'build')
    op.drop_constraint('unq_job_number', 'job')
