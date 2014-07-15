"""add latest green build table

Revision ID: 19b8969073ab
Revises: 4d235d421320
Create Date: 2014-07-10 10:53:34.415990

"""

# revision identifiers, used by Alembic.
revision = '19b8969073ab'
down_revision = '4d235d421320'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'latest_green_build',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('branch', sa.String(length=128), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.ForeignKeyConstraint(['build_id'], ['build.id'], ),
        sa.UniqueConstraint('project_id', 'branch', name='unq_project_branch')
    )


def downgrade():
    op.drop_table('latest_green_build')
