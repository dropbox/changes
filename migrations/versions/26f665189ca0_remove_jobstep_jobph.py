"""Remove JobStep/JobPhase repository_id

Revision ID: 26f665189ca0
Revises: 524b3c27203b
Create Date: 2014-01-05 22:01:02.648719

"""

# revision identifiers, used by Alembic.
revision = '26f665189ca0'
down_revision = '524b3c27203b'

from alembic import op


def upgrade():
    op.drop_column('jobstep', 'repository_id')
    op.drop_column('jobphase', 'repository_id')


def downgrade():
    raise NotImplementedError
