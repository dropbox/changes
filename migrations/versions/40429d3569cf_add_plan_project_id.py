"""Add Plan.project_id

Revision ID: 40429d3569cf
Revises: 36cbde703cc0
Create Date: 2014-10-09 14:38:51.043652

"""

# revision identifiers, used by Alembic.
revision = '40429d3569cf'
down_revision = '36cbde703cc0'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('plan', sa.Column('project_id', sa.GUID(), nullable=True))
    op.create_foreign_key('plan_project_id_fkey', 'plan', 'project', ['project_id'], ['id'], ondelete='CASCADE')


def downgrade():
    op.drop_column('plan', 'project_id')
