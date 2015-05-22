"""create flakyteststat table

Revision ID: 1c537486cef7
Revises: 3c93047c66c8
Create Date: 2015-05-20 17:25:02.213262

"""

# revision identifiers, used by Alembic.
revision = '1c537486cef7'
down_revision = '3c93047c66c8'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('flakyteststat',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('last_flaky_run_id', sa.GUID(), nullable=False),
        sa.Column('flaky_runs', sa.Integer(), nullable=False),
        sa.Column('passing_runs', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['last_flaky_run_id'], ['test.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('name', 'project_id', 'end_date', name='unq_name_per_project_per_day'))
    op.create_index('idx_flakyteststat_end_date', 'flakyteststat', ['end_date'])


def downgrade():
    op.drop_table('flakyteststat')
