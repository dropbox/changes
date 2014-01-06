"""Remove Job.{author_id,repository_id,patch_id,revision_sha,message,target,cause,parent_id}

Revision ID: 524b3c27203b
Revises: 3042d0ca43bf
Create Date: 2014-01-05 16:36:43.476520

"""

# revision identifiers, used by Alembic.
revision = '524b3c27203b'
down_revision = '3042d0ca43bf'

from alembic import op


def upgrade():
    op.drop_column('job', 'revision_sha')
    op.drop_column('job', 'patch_id')
    op.drop_column('job', 'author_id')
    op.drop_column('job', 'repository_id')
    op.drop_column('job', 'message')
    op.drop_column('job', 'target')
    op.drop_column('job', 'cause')
    op.drop_column('job', 'parent_id')


def downgrade():
    raise NotImplementedError
