"""*.family_id => build_id

Revision ID: 1ad857c78a0d
Revises: 545ba163595
Create Date: 2013-12-26 01:57:32.211057

"""

# revision identifiers, used by Alembic.
revision = '1ad857c78a0d'
down_revision = '545ba163595'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE job RENAME COLUMN family_id TO build_id')
    op.execute('ALTER TABLE jobplan RENAME COLUMN family_id TO build_id')


def downgrade():
    op.execute('ALTER TABLE job RENAME COLUMN build_id TO family_id')
    op.execute('ALTER TABLE jobplan RENAME COLUMN build_id TO family_id')
