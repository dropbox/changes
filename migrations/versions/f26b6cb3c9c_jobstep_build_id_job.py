"""JobStep.build_id => job_id

Revision ID: f26b6cb3c9c
Revises: 5026dbcee21d
Create Date: 2013-12-26 00:11:38.414155

"""

# revision identifiers, used by Alembic.
revision = 'f26b6cb3c9c'
down_revision = '5026dbcee21d'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE jobstep RENAME COLUMN build_id TO job_id')


def downgrade():
    op.execute('ALTER TABLE jobstep RENAME COLUMN job_id TO build_id')
