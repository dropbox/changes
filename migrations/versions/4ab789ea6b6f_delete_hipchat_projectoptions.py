"""Delete HipChat ProjectOptions

Revision ID: 4ab789ea6b6f
Revises: 2b1b01d74175
Create Date: 2015-04-24 16:37:49.769666

"""

# revision identifiers, used by Alembic.
revision = '4ab789ea6b6f'
down_revision = '2b1b01d74175'

from alembic import op
from sqlalchemy.sql import table

import sqlalchemy as sa


def upgrade():
    # hipchat options and events aren't needed or used anymore, so we remove them.
    # THIS CANNOT BE UNDONE.
    projectoptions_table = table(
        'projectoption',
        sa.Column('name', sa.String(length=64), nullable=False),
    )
    event_table = table(
        'event',
        sa.Column('type', sa.String(length=32), nullable=False),
    )
    op.get_bind().execute(
        projectoptions_table.delete().where(
            projectoptions_table.c.name.in_(['hipchat.room', 'hipchat.notify', 'hipchat.token'])))
    op.get_bind().execute(
        event_table.delete().where(event_table.c.type == 'hipchat'))


def downgrade():
    pass
