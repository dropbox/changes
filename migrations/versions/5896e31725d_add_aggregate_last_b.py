"""Add Aggregate*.last_build_id

Revision ID: 5896e31725d
Revises: 166d65e5a7e3
Create Date: 2013-12-05 13:50:57.818995

"""

# revision identifiers, used by Alembic.
revision = '5896e31725d'
down_revision = '166d65e5a7e3'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('aggtestgroup', sa.Column('last_build_id', sa.GUID()))
    op.add_column('aggtestsuite', sa.Column('last_build_id', sa.GUID()))

    op.execute("update aggtestgroup set last_build_id = first_build_id where first_build_id is null")
    op.execute("update aggtestsuite set last_build_id = first_build_id where first_build_id is null")

    op.alter_column('aggtestgroup', sa.Column('last_build_id', sa.GUID(), nullable=False))
    op.alter_column('aggtestsuite', sa.Column('last_build_id', sa.GUID(), nullable=False))


def downgrade():
    op.drop_column('aggtestsuite', 'last_build_id')
    op.drop_column('aggtestgroup', 'last_build_id')
