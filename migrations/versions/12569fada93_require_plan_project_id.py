"""Require Plan.project_id

Revision ID: 12569fada93
Revises: 4c3f2a63b7a7
Create Date: 2014-10-14 11:23:49.892957

"""

# revision identifiers, used by Alembic.
revision = '12569fada93'
down_revision = '4c3f2a63b7a7'

from alembic import op
from sqlalchemy.dialects import postgresql


def upgrade():
    op.alter_column('plan', 'project_id',
                    existing_type=postgresql.UUID(),
                    nullable=False)


def downgrade():
    op.alter_column('plan', 'project_id',
                    existing_type=postgresql.UUID(),
                    nullable=True)
