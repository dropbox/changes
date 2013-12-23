"""Add Build.family_id

Revision ID: cb99fdfb903
Revises: 1109e724859f
Create Date: 2013-12-23 11:32:17.060863

"""

# revision identifiers, used by Alembic.
revision = 'cb99fdfb903'
down_revision = '1109e724859f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('build', sa.Column('family_id', sa.GUID(), nullable=True))
    op.create_index('idx_build_family_id', 'build', ['family_id'])


def downgrade():
    op.drop_index('idx_build_family_id', 'build')
    op.drop_column('build', 'family_id')
