"""Add status index to task table.

Revision ID: 2c49f64c0d4a
Revises: 43397e521791
Create Date: 2016-09-29 15:45:51.104377

"""

# revision identifiers, used by Alembic.
revision = '2c49f64c0d4a'
down_revision = '43397e521791'

from alembic import op


def upgrade():
    op.create_index('idx_task_status', 'task', ['status'], unique=False, postgresql_concurrently=True)


def downgrade():
    op.drop_index('idx_task_status', table_name='task')
