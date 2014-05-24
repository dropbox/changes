"""Fill TestGroup.result

Revision ID: 3edf6ec6abd5
Revises: 47e23df5a7ed
Create Date: 2013-11-05 14:08:23.068195

"""

from __future__ import absolute_import, print_function

# revision identifiers, used by Alembic.
revision = '3edf6ec6abd5'
down_revision = '47e23df5a7ed'

from alembic import op
from sqlalchemy.sql import select, table
import sqlalchemy as sa


def upgrade():
    from changes.constants import Result

    connection = op.get_bind()

    testgroups_table = table(
        'testgroup',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('result', sa.Enum(), nullable=True),
    )
    testgroups_m2m_table = table(
        'testgroup_test',
        sa.Column('group_id', sa.GUID(), nullable=False),
        sa.Column('test_id', sa.GUID(), nullable=False),
    )
    testcases_table = table(
        'test',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('result', sa.Enum(), nullable=True),
    )

    # perform data migrations
    for testgroup in connection.execute(testgroups_table.select()):
        # migrate group to suite
        print("Migrating TestGroup %s" % (testgroup.id,))

        query = select([testcases_table]).where(
            sa.and_(
                testgroups_m2m_table.c.test_id == testcases_table.c.id,
                testgroups_m2m_table.c.group_id == testgroup.id,
            )
        )

        result = Result.unknown
        for testcase in connection.execute(query):
            result = max(result, Result(testcase.result))

        connection.execute(
            testgroups_table.update().where(
                testgroups_table.c.id == testgroup.id,
            ).values({
                testgroups_table.c.result: result,
            })
        )


def downgrade():
    pass
