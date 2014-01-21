"""Unused indexes on Job

Revision ID: 4ae598236ef1
Revises: 4ffb7e1df217
Create Date: 2014-01-21 14:19:27.134472

"""

# revision identifiers, used by Alembic.
revision = '4ae598236ef1'
down_revision = '4ffb7e1df217'

from alembic import op


def upgrade():
    op.drop_index('idx_build_source_id', 'job')
    op.drop_index('idx_build_family_id', 'job')


def downgrade():
    raise NotImplementedError
