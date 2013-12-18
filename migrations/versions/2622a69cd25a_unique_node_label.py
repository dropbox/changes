"""Unique Node.label

Revision ID: 2622a69cd25a
Revises: 2c7cbd9b7e54
Create Date: 2013-12-18 12:42:30.583085

"""

# revision identifiers, used by Alembic.
revision = '2622a69cd25a'
down_revision = '2c7cbd9b7e54'

from alembic import op


def upgrade():
    op.create_unique_constraint('unq_node_label', 'node', ['label'])


def downgrade():
    op.drop_constraint('unq_node_label', 'node')
