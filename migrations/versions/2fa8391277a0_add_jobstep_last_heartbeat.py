"""Add JobStep.last_heartbeat

Revision ID: 2fa8391277a0
Revises: 3768db8af6ea
Create Date: 2014-11-04 16:14:32.624975

"""

# revision identifiers, used by Alembic.
revision = '2fa8391277a0'
down_revision = '3768db8af6ea'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('jobstep', sa.Column('last_heartbeat', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('jobstep', 'last_heartbeat')
