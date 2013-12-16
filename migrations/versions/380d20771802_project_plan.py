"""Project <=> Plan

Revision ID: 380d20771802
Revises: 1d806848a73f
Create Date: 2013-12-16 14:38:39.941404

"""

# revision identifiers, used by Alembic.
revision = '380d20771802'
down_revision = '1d806848a73f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'project_plan',
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('plan_id', sa.GUID(), nullable=False),
        sa.ForeignKeyConstraint(['plan_id'], ['plan.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.PrimaryKeyConstraint('project_id', 'plan_id')
    )


def downgrade():
    op.drop_table('project_plan')
