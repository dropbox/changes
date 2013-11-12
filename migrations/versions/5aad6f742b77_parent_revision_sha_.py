"""parent_revision_sha => revision_sha

Revision ID: 5aad6f742b77
Revises: 2d82db02b3ef
Create Date: 2013-11-11 17:05:31.671178

"""

# revision identifiers, used by Alembic.
revision = '5aad6f742b77'
down_revision = '2d82db02b3ef'

from alembic import op


def upgrade():
    op.execute("update build set revision_sha = parent_revision_sha")


def downgrade():
    pass
