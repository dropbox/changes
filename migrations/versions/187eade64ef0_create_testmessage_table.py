"""Create testmessage table

Revision ID: 187eade64ef0
Revises: 016f138b2da8
Create Date: 2016-06-21 16:11:47.905481

"""

# revision identifiers, used by Alembic.
revision = '187eade64ef0'
down_revision = '016f138b2da8'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'testmessage',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('test_id', sa.GUID(), nullable=False),
        sa.Column('artifact_id', sa.GUID(), nullable=False),
        sa.Column('start_offset', sa.Integer(), nullable=False),
        sa.Column('length', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['test_id'], ['test.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['artifact_id'], ['artifact.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_testmessage_test_id', 'testmessage', ['test_id'], unique=False)


def downgrade():
    op.drop_table('testmessage')
