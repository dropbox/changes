"""Backfill TestCase leaves

Revision ID: 2b71d67ef04d
Revises: 3edf6ec6abd5
Create Date: 2013-11-07 12:48:43.717544

"""

# revision identifiers, used by Alembic.
revision = '2b71d67ef04d'
down_revision = '3edf6ec6abd5'

from alembic import op
from uuid import uuid4
from sqlalchemy.sql import table
import sqlalchemy as sa


def upgrade():
    from changes.constants import Result

    connection = op.get_bind()

    testgroups_table = table(
        'testgroup',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('name_sha', sa.String(length=40), nullable=False),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('num_tests', sa.Integer(), nullable=True),
        sa.Column('num_failed', sa.Integer(), nullable=True),
        sa.Column('name', sa.Text(), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=True),
    )
    testgroups_m2m_table = table(
        'testgroup_test',
        sa.Column('group_id', sa.GUID(), nullable=False),
        sa.Column('test_id', sa.GUID(), nullable=False),
    )
    testcases_table = table(
        'test',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('package', sa.Text(), nullable=True),
        sa.Column('name', sa.Text(), nullable=True),
        sa.Column('label_sha', sa.String(length=40), nullable=False),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('result', sa.Enum(), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=True),
    )

    for testcase in connection.execute(testcases_table.select()):
        print "Migrating TestCase %s" % (testcase.id,)

        if testcase.package:
            full_name = testcase.package + '.' + testcase.name
        else:
            full_name = testcase.name
        group_id = uuid4()

        # find the parent
        result = connection.execute(testgroups_table.select().where(sa.and_(
            testgroups_table.c.build_id == testcase.build_id,
            testgroups_table.c.name == testcase.packae or testcase.name.rsplit('.', 1)[0],
        )).limit(1)).fetchone()

        connection.execute(
            testgroups_table.insert().values(
                id=group_id,
                build_id=testcase.build_id,
                project_id=testcase.project_id,
                name=full_name,
                name_sha=testcase.label_sha,
                date_created=testcase.date_created,
                duration=testcase.duration,
                parent_id=result.id,
                result=testcase.result,
                num_tests=1,
                num_failed=1 if testcase.result == Result.failed else 0,
            )
        )

        connection.execute(
            testgroups_m2m_table.insert().values(
                group_id=group_id,
                test_id=testcase.id,
            )
        )


def downgrade():
    pass
