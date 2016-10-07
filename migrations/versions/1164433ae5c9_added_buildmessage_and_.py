"""added buildmessage and bazeltargetmessage tables

Revision ID: 1164433ae5c9
Revises: 181adec926e2
Create Date: 2016-09-27 18:49:14.886600

"""

# revision identifiers, used by Alembic.
revision = '1164433ae5c9'
down_revision = '181adec926e2'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('buildmessage',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['build_id'], ['build.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('bazeltargetmessage',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('target_id', sa.GUID(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['target_id'], ['bazeltarget.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('bazeltargetmessage')
    op.drop_table('buildmessage')
