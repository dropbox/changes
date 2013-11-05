"""Remove Author.name unique constraint

Revision ID: 520eba1ce36e
Revises: 18c045b75331
Create Date: 2013-11-04 19:20:04.277883

"""

# revision identifiers, used by Alembic.
revision = '520eba1ce36e'
down_revision = '18c045b75331'

from alembic import op


def upgrade():
    op.drop_index('author_name_key')


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    pass
    ### end Alembic commands ###
