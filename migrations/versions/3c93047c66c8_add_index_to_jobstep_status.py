"""Add index to JobStep.status

Revision ID: 3c93047c66c8
Revises: 4ab789ea6b6f
Create Date: 2015-04-28 22:55:23.139295

"""

# revision identifiers, used by Alembic.
revision = '3c93047c66c8'
down_revision = '4ab789ea6b6f'

from alembic import op


def upgrade():
    op.create_index('idx_jobstep_status', 'jobstep', ['status'], unique=False)


def downgrade():
    op.drop_index('idx_jobstep_status', table_name='jobstep')
