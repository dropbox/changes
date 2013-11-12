"""Fill target

Revision ID: 4901f27ade8e
Revises: 52bcea82b482
Create Date: 2013-11-11 17:25:38.930307

"""

# revision identifiers, used by Alembic.
revision = '4901f27ade8e'
down_revision = '52bcea82b482'

from alembic import op


def upgrade():
    op.execute("update build set target = substr(revision_sha, 0, 12) where target is null and revision_sha is not null")


def downgrade():
    pass
