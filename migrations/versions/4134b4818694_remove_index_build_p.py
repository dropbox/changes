"""Remove index Build.project_id

Revision ID: 4134b4818694
Revises: f2c8d15416b
Create Date: 2013-12-03 16:18:03.550867

"""

# revision identifiers, used by Alembic.
revision = '4134b4818694'
down_revision = 'f2c8d15416b'

from alembic import op


def upgrade():
    op.drop_index('idx_build_project_id', 'build')


def downgrade():
    pass
