"""FileCoverage.build_id => job_id

Revision ID: 256ab638deaa
Revises: 37244bf4e3f5
Create Date: 2013-12-26 01:47:50.855439

"""

# revision identifiers, used by Alembic.
revision = '256ab638deaa'
down_revision = '37244bf4e3f5'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE filecoverage RENAME COLUMN build_id TO job_id')


def downgrade():
    op.execute('ALTER TABLE filecoverage RENAME COLUMN job_id TO build_id')
