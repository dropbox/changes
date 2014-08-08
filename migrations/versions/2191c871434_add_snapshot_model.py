"""Add snapshot model

Revision ID: 2191c871434
Revises: 19168fe64c41
Create Date: 2014-07-17 17:21:42.915797

"""

# revision identifiers, used by Alembic.
revision = '2191c871434'
down_revision = '19168fe64c41'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'snapshot',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=True),
        sa.Column('status', sa.Enum(), server_default='0', nullable=False),
        sa.ForeignKeyConstraint(['build_id'], ['build.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('snapshot')
