"""Add TestCase.step_id

Revision ID: 3265d2120c82
Revises: 21c9439330f
Create Date: 2014-04-02 15:26:58.967387

"""

# revision identifiers, used by Alembic.
revision = '3265d2120c82'
down_revision = '21c9439330f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('test', sa.Column('step_id', sa.GUID(), nullable=True))
    op.create_foreign_key('test_step_id_fkey', 'test', 'jobstep', ['step_id'], ['id'], ondelete='CASCADE')
    op.create_index('idx_test_step_id', 'test', ['step_id'])


def downgrade():
    op.drop_column('test', 'step_id')
