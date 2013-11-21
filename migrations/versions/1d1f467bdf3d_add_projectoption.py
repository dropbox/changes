"""Add ProjectOption

Revision ID: 1d1f467bdf3d
Revises: 105d4dd82a0a
Create Date: 2013-11-20 16:04:25.408018

"""

# revision identifiers, used by Alembic.
revision = '1d1f467bdf3d'
down_revision = '105d4dd82a0a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'projectoption',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'name', name='unq_projectoption_name')
    )


def downgrade():
    op.drop_table('projectoption')
