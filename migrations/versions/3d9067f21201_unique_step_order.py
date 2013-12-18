"""Unique Step.order

Revision ID: 3d9067f21201
Revises: 2622a69cd25a
Create Date: 2013-12-18 15:06:47.035804

"""

# revision identifiers, used by Alembic.
revision = '3d9067f21201'
down_revision = '2622a69cd25a'

from alembic import op


def upgrade():
    op.create_unique_constraint('unq_step_key', 'step', ['plan_id', 'order'])
    op.drop_index('idx_step_plan_id', 'step')


def downgrade():
    op.create_index('idx_step_plan_id', 'step', ['plan_id'])
    op.drop_constraint('unq_step_key', 'step')
