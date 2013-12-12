"""Add build plans

Revision ID: ff220d76c11
Revises: 153b703a46ea
Create Date: 2013-12-11 16:12:18.309606

"""

# revision identifiers, used by Alembic.
revision = 'ff220d76c11'
down_revision = '153b703a46ea'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'plan',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('label', sa.String(length=128), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=False),
        sa.Column('date_modified', sa.DateTime(), nullable=False),
        sa.Column('data', sa.JSONEncodedDict(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'step',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('plan_id', sa.GUID(), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=False),
        sa.Column('date_modified', sa.DateTime(), nullable=False),
        sa.Column('implementation', sa.String(length=128), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('data', sa.JSONEncodedDict(), nullable=True),
        sa.CheckConstraint('step."order" >= 0', name='chk_step_order_positive'),
        sa.ForeignKeyConstraint(['plan_id'], ['plan.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_step_plan_id', 'step', ['plan_id'])
    op.create_table(
        'buildfamily',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('repository_id', sa.GUID(), nullable=False),
        sa.Column('revision_sha', sa.String(length=40), nullable=True),
        sa.Column('patch_id', sa.GUID(), nullable=True),
        sa.Column('author_id', sa.GUID(), nullable=True),
        sa.Column('cause', sa.Enum(), nullable=False),
        sa.Column('label', sa.String(length=128), nullable=False),
        sa.Column('target', sa.String(length=128), nullable=True),
        sa.Column('status', sa.Enum(), nullable=False),
        sa.Column('result', sa.Enum(), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('date_started', sa.DateTime(), nullable=True),
        sa.Column('date_finished', sa.DateTime(), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.Column('date_modified', sa.DateTime(), nullable=True),
        sa.Column('data', sa.JSONEncodedDict(), nullable=True),
        sa.ForeignKeyConstraint(['author_id'], ['author.id'], ),
        sa.ForeignKeyConstraint(['patch_id'], ['patch.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.ForeignKeyConstraint(['repository_id'], ['repository.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_buildfamily_project_id', 'buildfamily', ['project_id'])
    op.create_index('idx_buildfamily_repository_revision', 'buildfamily', ['repository_id', 'revision_sha'])
    op.create_index('idx_buildfamily_patch_id', 'buildfamily', ['patch_id'])
    op.create_index('idx_buildfamily_author_id', 'buildfamily', ['author_id'])

    op.create_table(
        'buildplan',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('family_id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('plan_id', sa.GUID(), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.Column('date_modified', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['build_id'], ['build.id'], ),
        sa.ForeignKeyConstraint(['family_id'], ['buildfamily.id'], ),
        sa.ForeignKeyConstraint(['plan_id'], ['plan.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_buildplan_project_id', 'buildplan', ['project_id'])
    op.create_index('idx_buildplan_family_id', 'buildplan', ['family_id'])
    op.create_index('idx_buildplan_build_id', 'buildplan', ['build_id'])
    op.create_index('idx_buildplan_plan_id', 'buildplan', ['plan_id'])


def downgrade():
    op.drop_table('buildplan')
    op.drop_table('buildfamily')
    op.drop_table('step')
    op.drop_table('plan')
