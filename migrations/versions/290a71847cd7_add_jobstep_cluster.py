"""add jobstep cluster

Revision ID: 290a71847cd7
Revises: 41c7ef24fd4c
Create Date: 2016-01-11 14:07:49.879954

"""

# revision identifiers, used by Alembic.
revision = '290a71847cd7'
down_revision = '41c7ef24fd4c'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('jobstep', sa.Column('cluster', sa.String(length=128),
                                   nullable=True))
    op.create_index('idx_jobstep_cluster', 'jobstep', ['cluster'])


def downgrade():
    # also drops the index
    op.drop_column('jobstep', 'cluster')
