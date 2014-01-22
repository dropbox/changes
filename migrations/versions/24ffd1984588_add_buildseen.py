"""Add BuildSeen

Revision ID: 24ffd1984588
Revises: 97786e74292
Create Date: 2014-01-22 11:13:41.168990

"""

# revision identifiers, used by Alembic.
revision = '24ffd1984588'
down_revision = '97786e74292'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'buildseen',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('user_id', sa.GUID(), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('build_id', 'user_id', name='unq_buildseen_entity')
    )
    op.create_foreign_key('buildseen_build_id_fkey', 'buildseen', 'build', ['build_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('buildseen_user_id_fkey', 'buildseen', 'user', ['user_id'], ['id'], ondelete='CASCADE')


def downgrade():
    op.drop_table('buildseen')
