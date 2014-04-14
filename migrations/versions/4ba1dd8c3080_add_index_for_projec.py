"""Add index for project test list

Revision ID: 4ba1dd8c3080
Revises: 2c380be0a31e
Create Date: 2014-04-14 11:08:05.598439

"""

# revision identifiers, used by Alembic.
revision = '4ba1dd8c3080'
down_revision = '2c380be0a31e'

from alembic import op


def upgrade():
    op.create_index('idx_test_project_key', 'test', ['project_id', 'label_sha'])


def downgrade():
    op.drop_index('idx_test_project_key', 'test')
