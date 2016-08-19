"""add project_permissions column to user

Revision ID: 460741ff1212
Revises: 3b94584c761e
Create Date: 2016-08-19 09:26:10.731482

"""

# revision identifiers, used by Alembic.
revision = '460741ff1212'
down_revision = '3b94584c761e'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.add_column('user', sa.Column('project_permissions', postgresql.ARRAY(sa.String(length=256)), nullable=False, default=[]))


def downgrade():
    op.drop_column('user', 'project_permissions')
