"""Change LogSource constraint

Revision ID: 3b22c1663664
Revises: 15f131d88adf
Create Date: 2014-06-25 01:07:42.217354

"""

# revision identifiers, used by Alembic.
revision = '3b22c1663664'
down_revision = '15f131d88adf'

from alembic import op


def upgrade():
    op.create_unique_constraint(
        'unq_logsource_key2', 'logsource', ['step_id', 'name'])
    op.drop_constraint('unq_logsource_key', 'logsource')


def downgrade():
    raise NotImplementedError
