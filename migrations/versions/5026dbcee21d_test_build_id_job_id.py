"""Test*.build_id => job_id

Revision ID: 5026dbcee21d
Revises: 42e9d35a4098
Create Date: 2013-12-25 23:50:12.762986

"""

# revision identifiers, used by Alembic.
revision = '5026dbcee21d'
down_revision = '42e9d35a4098'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE test RENAME COLUMN build_id TO job_id')
    op.execute('ALTER TABLE testgroup RENAME COLUMN build_id TO job_id')
    op.execute('ALTER TABLE testsuite RENAME COLUMN build_id TO job_id')


def downgrade():
    op.execute('ALTER TABLE test RENAME COLUMN job_id TO build_id')
    op.execute('ALTER TABLE testgroup RENAME COLUMN job_id TO build_id')
    op.execute('ALTER TABLE testsuite RENAME COLUMN job_id TO build_id')
