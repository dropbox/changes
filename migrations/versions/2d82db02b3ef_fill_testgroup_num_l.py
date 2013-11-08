"""Fill TestGroup.num_leaves

Revision ID: 2d82db02b3ef
Revises: 4640ecd97c82
Create Date: 2013-11-08 13:14:05.257558

"""

# revision identifiers, used by Alembic.
revision = '2d82db02b3ef'
down_revision = '4640ecd97c82'

from alembic import op


def upgrade():
    op.execute("""
        update testgroup as a
        set num_leaves = (
            select count(*)
            from testgroup as b
            where a.id = b.parent_id
        )
    """)


def downgrade():
    pass
