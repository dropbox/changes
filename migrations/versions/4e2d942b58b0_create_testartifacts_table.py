"""create_testartifacts_table

Revision ID: 4e2d942b58b0
Revises: 2fa8391277a0
Create Date: 2014-11-12 13:33:03.442972

"""

# revision identifiers, used by Alembic.
revision = '4e2d942b58b0'
down_revision = '234a17cf1424'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'testartifact',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('test_id', sa.GUID(), nullable=False),
        sa.Column('name', sa.String(length=256), nullable=False),
        sa.Column('type', sa.Enum(), server_default='0', nullable=False),
        sa.Column('file', sa.FileStorage(), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=True),

        sa.ForeignKeyConstraint(['test_id'], ['test.id'], ),
        sa.PrimaryKeyConstraint('id'),

        sa.Index('idx_test_id', 'test_id'),
    )


def downgrade():
    op.drop_table('testartifact')
