"""Create index in flakyteststat for test_id

Revision ID: 3b94584c761e
Revises: 3be107806e62
Create Date: 2016-07-13 14:03:31.967630

"""

# revision identifiers, used by Alembic.
revision = '3b94584c761e'
down_revision = '3be107806e62'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_index('idx_flakyteststat_last_flaky_run_id', 'flakyteststat', ['last_flaky_run_id'])


def downgrade():
    op.drop_index('idx_flakyteststat_last_flaky_run_id', 'flakyteststat')
