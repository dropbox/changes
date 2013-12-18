"""Add Source

Revision ID: 2c7cbd9b7e54
Revises: 380d20771802
Create Date: 2013-12-17 13:53:19.836264

"""

# revision identifiers, used by Alembic.
revision = '2c7cbd9b7e54'
down_revision = '380d20771802'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'source',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('repository_id', sa.GUID(), nullable=False),
        sa.Column('patch_id', sa.GUID(), nullable=True),
        sa.Column('revision_sha', sa.String(length=40), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['patch_id'], ['patch.id']),
        sa.ForeignKeyConstraint(['repository_id'], ['repository.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.add_column('build', sa.Column('source_id', sa.GUID(), nullable=True))
    op.add_column('buildfamily', sa.Column('source_id', sa.GUID(), nullable=True))
    op.create_index('idx_build_source_id', 'build', ['source_id'])
    op.create_index('idx_buildfamily_source_id', 'buildfamily', ['source_id'])


def downgrade():
    op.drop_index('idx_build_source_id', 'build')
    op.drop_index('idx_buildfamily_source_id', 'buildfamily')
    op.drop_column('buildfamily', 'source_id')
    op.drop_column('build', 'source_id')
    op.drop_table('source')
