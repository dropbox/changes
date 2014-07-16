"""create jobstep command table

Revision ID: 3f6a69c14037
Revises: 21a9d1ebe15c
Create Date: 2014-07-15 15:47:01.960708

"""

# revision identifiers, used by Alembic.
revision = '3f6a69c14037'
down_revision = '21a9d1ebe15c'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table(
        'command',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('jobstep_id', sa.GUID(), nullable=False),
        sa.Column('label', sa.String(length=128), nullable=False),
        sa.Column('status', sa.Enum(), nullable=False),
        sa.Column('return_code', sa.Integer(), nullable=False),
        sa.Column('script', sa.Text(), nullable=False),
        sa.Column('env', sa.String(length=2048), nullable=True),
        sa.Column('cwd', sa.String(length=256), nullable=True),
        sa.Column('artifacts', postgresql.ARRAY(sa.String(length=256)), nullable=True),
        sa.Column('date_started', sa.DateTime(), nullable=True),
        sa.Column('date_finished', sa.DateTime(), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.Column('data', sa.JSONEncodedDict(), nullable=True),
        sa.ForeignKeyConstraint(['jobstep_id'], ['jobstep.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('command')
