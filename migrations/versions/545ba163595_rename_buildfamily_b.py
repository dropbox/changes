"""Rename BuildFamily => Build

Revision ID: 545ba163595
Revises: 256ab638deaa
Create Date: 2013-12-26 01:51:58.807080

"""

# revision identifiers, used by Alembic.
revision = '545ba163595'
down_revision = '256ab638deaa'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE buildfamily RENAME TO build')


def downgrade():
    op.execute('ALTER TABLE build RENAME TO buildfamily')
