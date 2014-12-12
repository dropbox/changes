"""Add Build.collection_id

Revision ID: 1cb3db431e29
Revises: 3aed22af8f4f
Create Date: 2014-12-10 22:00:33.463247

"""

# revision identifiers, used by Alembic.
revision = '1cb3db431e29'
down_revision = '3aed22af8f4f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('build', sa.Column('collection_id', sa.GUID(), nullable=True))
    op.create_index('idx_build_collection_id', 'build', ['collection_id'])


def downgrade():
    op.drop_index('idx_build_collection_id', 'build')
    op.drop_column('build', 'collection_id')
