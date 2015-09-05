"""Add jobstep replacement_id

Revision ID: 3e85891e90bb
Revises: 291978a5d5e4
Create Date: 2015-08-31 16:19:46.669260

"""

# revision identifiers, used by Alembic.
revision = '3e85891e90bb'
down_revision = '291978a5d5e4'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('jobstep', sa.Column('replacement_id', sa.GUID(),
                                       sa.ForeignKey('jobstep.id', ondelete="CASCADE"),
                                       unique=True, nullable=True))


def downgrade():
    op.drop_column('jobstep', 'replacement_id')
