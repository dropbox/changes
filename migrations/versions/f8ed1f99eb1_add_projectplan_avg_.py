"""Add ProjectPlan.avg_build_time

Revision ID: f8ed1f99eb1
Revises: 25d63e09ea3b
Create Date: 2014-01-02 16:12:43.339060

"""

# revision identifiers, used by Alembic.
revision = 'f8ed1f99eb1'
down_revision = '25d63e09ea3b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('project_plan', sa.Column('avg_build_time', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('project_plan', 'avg_build_time')
