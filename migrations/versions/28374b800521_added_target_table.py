"""Added target table

Revision ID: 28374b800521
Revises: 460741ff1212
Create Date: 2016-08-24 23:55:14.231624

"""

# revision identifiers, used by Alembic.
revision = '28374b800521'
down_revision = '460741ff1212'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'bazeltarget',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('step_id', sa.GUID(), nullable=False),
        sa.Column('job_id', sa.GUID(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum(), nullable=False),
        sa.Column('result', sa.Enum(), nullable=False),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['step_id'], ['jobstep.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['job_id'], ['job.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.add_column('test', sa.Column('target_id', sa.GUID(), nullable=True))
    op.create_foreign_key('test_target_id_fkey', 'test', 'bazeltarget', ['target_id'], ['id'], ondelete='CASCADE')


def downgrade():
    op.drop_constraint('test_target_id_fkey', 'test')
    op.drop_column('test', 'target_id')
    op.drop_table('bazeltarget')
