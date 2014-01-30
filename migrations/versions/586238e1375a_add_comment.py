"""Add Comment

Revision ID: 586238e1375a
Revises: 24ffd1984588
Create Date: 2014-01-30 12:52:35.146236

"""

# revision identifiers, used by Alembic.
revision = '586238e1375a'
down_revision = '24ffd1984588'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'comment',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('user_id', sa.GUID(), nullable=False),
        sa.Column('job_id', sa.GUID(), nullable=True),
        sa.Column('text', sa.Text(), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['build_id'], ['build.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['job.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('comment')
