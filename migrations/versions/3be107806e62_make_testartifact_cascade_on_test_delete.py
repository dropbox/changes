"""Make testartifact cascade on test delete

Revision ID: 3be107806e62
Revises: 3bf1066f4935
Create Date: 2016-07-06 18:42:33.893405

"""

# revision identifiers, used by Alembic.
revision = '3be107806e62'
down_revision = '3bf1066f4935'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_constraint('testartifact_test_id_fkey', 'testartifact')
    op.create_foreign_key('testartifact_test_id_fkey', 'testartifact', 'test', ['test_id'], ['id'], ondelete='CASCADE')


def downgrade():
    op.drop_constraint('testartifact_test_id_fkey', 'testartifact')
    op.create_foreign_key('testartifact_test_id_fkey', 'testartifact', 'test', ['test_id'], ['id'])
