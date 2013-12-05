"""Add AggregateTest{Group,Suite}

Revision ID: 166d65e5a7e3
Revises: 21b7c3b2ce88
Create Date: 2013-12-04 13:19:26.702555

"""

# revision identifiers, used by Alembic.
revision = '166d65e5a7e3'
down_revision = '21b7c3b2ce88'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'aggtestsuite',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('name_sha', sa.String(length=40), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('first_build_id', sa.GUID(), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['first_build_id'], ['build.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'project_id', 'name_sha', name='unq_aggtestsuite_key')
    )
    op.create_index('idx_aggtestsuite_first_build_id', 'aggtestsuite', ['first_build_id'])

    op.create_table(
        'aggtestgroup',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('suite_id', sa.GUID(), nullable=True),
        sa.Column('parent_id', sa.GUID(), nullable=True),
        sa.Column('name_sha', sa.String(length=40), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('first_build_id', sa.GUID(), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['first_build_id'], ['build.id'], ),
        sa.ForeignKeyConstraint(['parent_id'], ['aggtestgroup.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.ForeignKeyConstraint(['suite_id'], ['aggtestsuite.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'project_id', 'suite_id', 'name_sha', name='unq_aggtestgroup_key')
    )
    op.create_index('idx_aggtestgroup_suite_id', 'aggtestgroup', ['suite_id'])
    op.create_index('idx_aggtestgroup_parent_id', 'aggtestgroup', ['parent_id'])
    op.create_index('idx_aggtestgroup_first_build_id', 'aggtestgroup', ['first_build_id'])


def downgrade():
    op.drop_table('aggtestgroup')
    op.drop_table('aggtestsuite')
