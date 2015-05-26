"""add label_sha index

Revision ID: 2f12902f7f55
Revises: 1c537486cef7
Create Date: 2015-05-26 09:33:50.930456

"""

# revision identifiers, used by Alembic.
revision = '2f12902f7f55'
down_revision = '1c537486cef7'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_index('idx_test_label_sha', 'test', ['label_sha'])

def downgrade():
    op.drop_index('idx_test_label_sha', 'test')
