"""Set ON DELETE CASCADE on Step.*

Revision ID: 554f414d4c46
Revises: 306fefe51dc6
Create Date: 2013-12-23 16:46:05.137414

"""

# revision identifiers, used by Alembic.
revision = '554f414d4c46'
down_revision = '306fefe51dc6'

from alembic import op


def upgrade():
    op.drop_constraint('step_plan_id_fkey', 'step')
    op.create_foreign_key('step_plan_id_fkey', 'step', 'plan', ['plan_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass
