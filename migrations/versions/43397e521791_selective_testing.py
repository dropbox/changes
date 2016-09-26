"""selective testing

Revision ID: 43397e521791
Revises: 28374b800521
Create Date: 2016-09-21 21:49:23.276258

"""

# revision identifiers, used by Alembic.
revision = '43397e521791'
down_revision = '28374b800521'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table(
        'revisionresult',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=True),
        sa.Column('revision_sha', sa.String(
            length=40), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('result', sa.Enum(), nullable=False),
        sa.ForeignKeyConstraint(['build_id'], ['build.id'], ),
        sa.ForeignKeyConstraint(
            ['project_id'], ['project.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'revision_sha',
                            name='unq_project_revision_pair')
    )
    op.add_column('bazeltarget', sa.Column('result_source',
                                           sa.Enum()))
    op.alter_column('bazeltarget', 'step_id',
                    existing_type=postgresql.UUID(),
                    nullable=True)
    # don't do selective testing by default
    op.add_column('build', sa.Column('selective_testing_policy',
                                     sa.Enum()))


def downgrade():
    op.drop_column('build', 'selective_testing_policy')
    op.alter_column('bazeltarget', 'step_id',
                    existing_type=postgresql.UUID(),
                    nullable=False)
    op.drop_column('bazeltarget', 'result_source')
    op.drop_table('revisionresult')
