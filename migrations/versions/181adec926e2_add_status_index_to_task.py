"""Add status index to task

Revision ID: 181adec926e2
Revises: 43397e521791
Create Date: 2016-10-03 17:41:44.038137

"""

# revision identifiers, used by Alembic.
revision = '181adec926e2'
down_revision = '43397e521791'

from alembic import op


def upgrade():
    op.create_index('idx_task_status', 'task', ['status'], unique=False)


def downgrade():
    op.drop_index('id_task_status', table_name='task')
