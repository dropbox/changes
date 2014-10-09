"""Replace allow-patches with patches-trigger

Revision ID: 2c6662281b66
Revises: fe743605e1a
Create Date: 2014-10-08 22:13:24.112295

"""

# revision identifiers, used by Alembic.
revision = '2c6662281b66'
down_revision = 'fe743605e1a'

from alembic import op
from sqlalchemy.sql import select, table

import sqlalchemy as sa


def upgrade():
    # Don't delete any itemoption rows because that's irreversible. Those must
    #   be deleted manually.
    print("Starting projectoption table migration...")

    # Rename build.allow-patches to build.patches-trigger
    projectoptions_table = table(
        'projectoption',
        sa.Column('name', sa.String(length=64), nullable=False),
    )

    # Perform the migration
    op.get_bind().execute(
        projectoptions_table.update().where(
            projectoptions_table.c.name == 'build.allow-patches',
        ).values({
            projectoptions_table.c.name: 'phabricator.diff-trigger',
        })
    )
    print("Migration complete.")


def downgrade():

    projectoptions_table = table(
        'projectoption',
        sa.Column('name', sa.String(length=64), nullable=False),
    )

    # Perform the migration
    op.get_bind().execute(
        projectoptions_table.update().where(
            projectoptions_table.c.name == 'phabricator.diff-trigger',
        ).values({
            projectoptions_table.c.name: 'build.allow-patches',
        })
    )
