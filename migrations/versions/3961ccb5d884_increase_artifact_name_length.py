"""increase artifact name length

Revision ID: 3961ccb5d884
Revises: 1b229c83511d
Create Date: 2015-11-05 15:34:28.189700

"""

# revision identifiers, used by Alembic.
revision = '3961ccb5d884'
down_revision = '1b229c83511d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('artifact', 'name', type_=sa.VARCHAR(1024))


def downgrade():
    op.alter_column('artifact', 'name', type_=sa.VARCHAR(128))
