"""Remove RemoteEntity

Revision ID: 234a17cf1424
Revises: 2fa8391277a0
Create Date: 2014-11-19 17:50:44.488598

"""

# revision identifiers, used by Alembic.
revision = '234a17cf1424'
down_revision = '2fa8391277a0'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.drop_table('remoteentity')


def downgrade():
    op.create_table(
        'remoteentity',
        sa.Column('id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column('type', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('provider', sa.VARCHAR(length=128), autoincrement=False, nullable=False),
        sa.Column('remote_id', sa.VARCHAR(length=128), autoincrement=False, nullable=False),
        sa.Column('internal_id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column('data', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('date_created', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint('id', name=u'remoteentity_pkey')
    )
