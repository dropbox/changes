"""Add Artifact.file

Revision ID: 4d235d421320
Revises: 19910015c867
Create Date: 2014-07-14 17:24:54.764351

"""

# revision identifiers, used by Alembic.
revision = '4d235d421320'
down_revision = '19910015c867'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('artifact', sa.Column('file', sa.FileStorage(), nullable=True))


def downgrade():
    op.drop_column('artifact', 'file')
