"""Update ON DELETE CASCADE to Test*

Revision ID: 1eefd7dfedb2
Revises: 2f3ba1e84a6f
Create Date: 2013-12-23 15:39:12.877828

"""

# revision identifiers, used by Alembic.
revision = '1eefd7dfedb2'
down_revision = '2f3ba1e84a6f'

from alembic import op


def upgrade():
    # Test
    op.drop_constraint('test_build_id_fkey', 'test')
    op.create_foreign_key('test_build_id_fkey', 'test', 'build', ['build_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('test_project_id_fkey', 'test')
    op.create_foreign_key('test_project_id_fkey', 'test', 'project', ['project_id'], ['id'], ondelete='CASCADE')

    # TestGroup
    op.drop_constraint('testgroup_build_id_fkey', 'testgroup')
    op.create_foreign_key('testgroup_build_id_fkey', 'testgroup', 'build', ['build_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('testgroup_project_id_fkey', 'testgroup')
    op.create_foreign_key('testgroup_project_id_fkey', 'testgroup', 'project', ['project_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('testgroup_parent_id_fkey', 'testgroup')
    op.create_foreign_key('testgroup_parent_id_fkey', 'testgroup', 'testgroup', ['parent_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('testgroup_suite_id_fkey', 'testgroup')
    op.create_foreign_key('testgroup_suite_id_fkey', 'testgroup', 'testsuite', ['suite_id'], ['id'], ondelete='CASCADE')

    # TestGroup <=> Test m2m
    op.drop_constraint('testgroup_test_group_id_fkey', 'testgroup_test')
    op.create_foreign_key('testgroup_test_group_id_fkey', 'testgroup_test', 'testgroup', ['group_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('testgroup_test_test_id_fkey', 'testgroup_test')
    op.create_foreign_key('testgroup_test_test_id_fkey', 'testgroup_test', 'test', ['test_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass
