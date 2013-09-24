"""Increase length of Build.label

Revision ID: 4e03cae8d0a2
Revises: 52300f21c50c
Create Date: 2013-09-23 20:02:38.456681

"""

# revision identifiers, used by Alembic.
revision = '4e03cae8d0a2'
down_revision = '52300f21c50c'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('build', 'label', type_=sa.String(length=128))


def downgrade():
    op.alter_column('build', 'label', type_=sa.String(length=64))
