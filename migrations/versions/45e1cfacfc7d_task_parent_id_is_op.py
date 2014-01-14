"""Task.parent_id is optional

Revision ID: 45e1cfacfc7d
Revises: 26dbd6ff063c
Create Date: 2014-01-13 16:23:03.890537

"""

# revision identifiers, used by Alembic.
revision = '45e1cfacfc7d'
down_revision = '26dbd6ff063c'

from alembic import op
from sqlalchemy.dialects import postgresql


def upgrade():
    op.alter_column('task', 'parent_id', existing_type=postgresql.UUID(),
                    nullable=True)


def downgrade():
    op.alter_column('task', 'parent_id', existing_type=postgresql.UUID(),
                    nullable=False)
