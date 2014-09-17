"""Remove RepositoryOption

Revision ID: fe743605e1a
Revises: 10403d977f5f
Create Date: 2014-09-17 15:17:09.925681

"""

# revision identifiers, used by Alembic.
revision = 'fe743605e1a'
down_revision = '10403d977f5f'

from alembic import op


def upgrade():
    op.drop_table('repositoryoption')


def downgrade():
    raise NotImplementedError
