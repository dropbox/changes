"""Migrate ProjectPlan

Revision ID: 4cd8cf6a0894
Revises: 40429d3569cf
Create Date: 2014-10-09 14:39:25.015079

"""

# revision identifiers, used by Alembic.
revision = '4cd8cf6a0894'
down_revision = '40429d3569cf'

from alembic import op
from sqlalchemy.sql import table
import sqlalchemy as sa


def upgrade():
    connection = op.get_bind()

    plan_table = table(
        'plan',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
    )

    project_plan_table = table(
        'project_plan',
        sa.Column('plan_id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
    )

    for project_plan in connection.execute(project_plan_table.select()):
        print("Migrating ProjectPlan plan_id=%s project_id=%s" % (
            project_plan.plan_id, project_plan.project_id))

        connection.execute(
            plan_table.update().where(
                plan_table.c.id == project_plan.plan_id,
            ).values({
                plan_table.c.project_id: project_plan.project_id,
            })
        )


def downgrade():
    pass
