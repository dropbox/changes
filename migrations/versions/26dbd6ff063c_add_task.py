"""Add Task

Revision ID: 26dbd6ff063c
Revises: 26c0affcb18a
Create Date: 2014-01-09 17:03:39.051795

"""

# revision identifiers, used by Alembic.
revision = '26dbd6ff063c'
down_revision = '26c0affcb18a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'task',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('task_name', sa.String(length=128), nullable=False),
        sa.Column('parent_id', sa.GUID(), nullable=False),
        sa.Column('child_id', sa.GUID(), nullable=False),
        sa.Column('status', sa.Enum(), nullable=False),
        sa.Column('result', sa.Enum(), nullable=False),
        sa.Column('num_retries', sa.Integer(), nullable=False),
        sa.Column('date_started', sa.DateTime(), nullable=True),
        sa.Column('date_finished', sa.DateTime(), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.Column('date_modified', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_name', 'parent_id', 'child_id', name='unq_task_entity')
    )

    op.create_index('idx_task_parent_id', 'task', ['parent_id', 'task_name'])
    op.create_index('idx_task_child_id', 'task', ['child_id', 'task_name'])


def downgrade():
    op.drop_table('task')
