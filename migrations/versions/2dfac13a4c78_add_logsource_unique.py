"""Add LogSource unique constraint on name

Revision ID: 2dfac13a4c78
Revises: 5896e31725d
Create Date: 2013-12-06 10:56:15.727933

"""

from __future__ import absolute_import, print_function

# revision identifiers, used by Alembic.
revision = '2dfac13a4c78'
down_revision = '5896e31725d'

from alembic import op
from sqlalchemy.sql import table, select
import sqlalchemy as sa


def upgrade():
    connection = op.get_bind()

    logsources_table = table(
        'logsource',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('name', sa.String(64), nullable=True),
    )
    logchunks_table = table(
        'logchunk',
        sa.Column('source_id', sa.GUID(), nullable=False),
    )

    done = set()

    for logsource in connection.execute(logsources_table.select()):
        # migrate group to suite
        key = (logsource.build_id, logsource.name)
        if key in done:
            continue

        print("Checking LogSource %s - %s" % (
            logsource.build_id, logsource.name))
        query = logchunks_table.delete().where(
            logchunks_table.c.source_id.in_(select([logchunks_table]).where(
                sa.and_(
                    logsources_table.c.build_id == logsource.build_id,
                    logsources_table.c.name == logsource.name,
                    logsources_table.c.id != logsource.id,
                ),
            ))
        )
        connection.execute(query)

        query = logsources_table.delete().where(
            sa.and_(
                logsources_table.c.build_id == logsource.build_id,
                logsources_table.c.name == logsource.name,
                logsources_table.c.id != logsource.id,
            )
        )

        connection.execute(query)

        done.add(key)

    op.create_unique_constraint(
        'unq_logsource_key', 'logsource', ['build_id', 'name'])
    op.drop_index('idx_logsource_build_id', 'logsource')


def downgrade():
    op.drop_constraint('unq_logsource_key', 'logsource')
    op.create_index('idx_logsource_build_id', 'logsource', ['build_id'])
