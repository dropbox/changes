"""Set ON DELETE CASCADE on Log*

Revision ID: 218e84b10a0e
Revises: 54a5c0c8793b
Create Date: 2013-12-23 16:39:13.642754

"""

# revision identifiers, used by Alembic.
revision = '218e84b10a0e'
down_revision = '54a5c0c8793b'

from alembic import op


def upgrade():
    op.drop_constraint('logsource_project_id_fkey', 'logsource')
    op.create_foreign_key('logsource_project_id_fkey', 'logsource', 'project', ['project_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('logsource_build_id_fkey', 'logsource')
    op.create_foreign_key('logsource_build_id_fkey', 'logsource', 'build', ['build_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('logchunk_project_id_fkey', 'logchunk')
    op.create_foreign_key('logchunk_project_id_fkey', 'logchunk', 'project', ['project_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('logchunk_build_id_fkey', 'logchunk')
    op.create_foreign_key('logchunk_build_id_fkey', 'logchunk', 'build', ['build_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('logchunk_source_id_fkey', 'logchunk')
    op.create_foreign_key('logchunk_source_id_fkey', 'logchunk', 'logsource', ['source_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass
