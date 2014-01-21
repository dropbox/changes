"""Unique JobPhase.{job_id,label}

Revision ID: 4ffb7e1df217
Revises: 545e104c5f5a
Create Date: 2014-01-21 11:12:10.408310

"""

# revision identifiers, used by Alembic.
revision = '4ffb7e1df217'
down_revision = '545e104c5f5a'

from alembic import op


def upgrade():
    op.create_unique_constraint('unq_jobphase_key', 'jobphase', ['job_id', 'label'])


def downgrade():
    op.drop_constraint('unq_jobphase_key', 'jobphase')
