"""Add JobStep.data

Revision ID: 26c0affcb18a
Revises: 4114cbbd0573
Create Date: 2014-01-07 16:44:48.524027

"""

# revision identifiers, used by Alembic.
revision = '26c0affcb18a'
down_revision = '4114cbbd0573'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('jobstep', sa.Column('data', sa.JSONEncodedDict(), nullable=True))


def downgrade():
    op.drop_column('jobstep', 'data')
