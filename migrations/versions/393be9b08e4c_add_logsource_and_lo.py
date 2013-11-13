"""Add LogSource and LogChunk

Revision ID: 393be9b08e4c
Revises: 4901f27ade8e
Create Date: 2013-11-12 11:05:50.757171

"""

# revision identifiers, used by Alembic.
revision = '393be9b08e4c'
down_revision = '4901f27ade8e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'logsource',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['build_id'], ['build.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('idx_logsource_project_id', 'logsource', ['project_id'])
    op.create_index('idx_logsource_build_id', 'logsource', ['build_id'])

    op.create_table(
        'logchunk',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('source_id', sa.GUID(), nullable=False),
        sa.Column('offset', sa.Integer(), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['build_id'], ['build.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.ForeignKeyConstraint(['source_id'], ['logsource.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('idx_logchunk_project_id', 'logchunk', ['project_id'])
    op.create_index('idx_logchunk_build_id', 'logchunk', ['build_id'])
    op.create_index('idx_logchunk_source_id', 'logchunk', ['source_id'])


def downgrade():
    op.drop_table('logchunk')
    op.drop_table('logsource')
