"""Unique BuildPlan.build

Revision ID: 1d806848a73f
Revises: ff220d76c11
Create Date: 2013-12-13 13:37:37.833620

"""

# revision identifiers, used by Alembic.
revision = '1d806848a73f'
down_revision = 'ff220d76c11'

from alembic import op


def upgrade():
    op.create_unique_constraint('unq_buildplan_build', 'buildplan', ['build_id'])
    op.drop_index('idx_buildplan_build_id', 'buildplan')


def downgrade():
    op.create_index('idx_buildplan_build_id', 'buildplan', ['build_id'])
    op.drop_constraint('unq_buildplan_build', 'buildplan')
