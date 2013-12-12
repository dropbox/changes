"""Replace Step/Phase with BuildStep/BuildPhase

Revision ID: 153b703a46ea
Revises: 2dfac13a4c78
Create Date: 2013-12-11 12:12:16.351785

"""

# revision identifiers, used by Alembic.
revision = '153b703a46ea'
down_revision = '2dfac13a4c78'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table(
        'buildphase',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('repository_id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('label', sa.String(length=128), nullable=False),
        sa.Column('status', sa.Enum(), nullable=False),
        sa.Column('result', sa.Enum(), nullable=False),
        sa.Column('date_started', sa.DateTime(), nullable=True),
        sa.Column('date_finished', sa.DateTime(), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['build_id'], ['build.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.ForeignKeyConstraint(['repository_id'], ['repository.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'buildstep',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('phase_id', sa.GUID(), nullable=False),
        sa.Column('repository_id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('label', sa.String(length=128), nullable=False),
        sa.Column('status', sa.Enum(), nullable=False),
        sa.Column('result', sa.Enum(), nullable=False),
        sa.Column('node_id', sa.GUID(), nullable=True),
        sa.Column('date_started', sa.DateTime(), nullable=True),
        sa.Column('date_finished', sa.DateTime(), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['build_id'], ['build.id'], ),
        sa.ForeignKeyConstraint(['node_id'], ['node.id'], ),
        sa.ForeignKeyConstraint(['phase_id'], ['buildphase.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.ForeignKeyConstraint(['repository_id'], ['repository.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.drop_table(u'step')
    op.drop_table(u'phase')


def downgrade():
    op.create_table(
        u'step',
        sa.Column(u'id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column(u'build_id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column(u'phase_id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column(u'repository_id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column(u'project_id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column(u'label', sa.VARCHAR(length=128), autoincrement=False, nullable=False),
        sa.Column(u'status', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(u'result', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(u'node_id', postgresql.UUID(), autoincrement=False, nullable=True),
        sa.Column(u'date_started', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column(u'date_finished', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column(u'date_created', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['build_id'], [u'build.id'], name=u'step_build_id_fkey'),
        sa.ForeignKeyConstraint(['node_id'], [u'node.id'], name=u'step_node_id_fkey'),
        sa.ForeignKeyConstraint(['phase_id'], [u'phase.id'], name=u'step_phase_id_fkey'),
        sa.ForeignKeyConstraint(['project_id'], [u'project.id'], name=u'step_project_id_fkey'),
        sa.ForeignKeyConstraint(['repository_id'], [u'repository.id'], name=u'step_repository_id_fkey'),
        sa.PrimaryKeyConstraint(u'id', name=u'step_pkey')
    )
    op.create_table(
        u'phase',
        sa.Column(u'id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column(u'build_id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column(u'repository_id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column(u'project_id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column(u'label', sa.VARCHAR(length=128), autoincrement=False, nullable=False),
        sa.Column(u'status', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(u'result', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(u'date_started', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column(u'date_finished', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column(u'date_created', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['build_id'], [u'build.id'], name=u'phase_build_id_fkey'),
        sa.ForeignKeyConstraint(['project_id'], [u'project.id'], name=u'phase_project_id_fkey'),
        sa.ForeignKeyConstraint(['repository_id'], [u'repository.id'], name=u'phase_repository_id_fkey'),
        sa.PrimaryKeyConstraint(u'id', name=u'phase_pkey')
    )
    op.drop_table('buildstep')
    op.drop_table('buildphase')
