"""add_logsource_in_artifact_store

Revision ID: 1b229c83511d
Revises: 382745ed4478
Create Date: 2015-10-07 14:55:58.423046

"""

# revision identifiers, used by Alembic.
revision = '1b229c83511d'
down_revision = '382745ed4478'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('logsource', sa.Column('in_artifact_store', sa.Boolean(), default=False))


def downgrade():
    op.drop_column('logsource', 'in_artifact_store')
