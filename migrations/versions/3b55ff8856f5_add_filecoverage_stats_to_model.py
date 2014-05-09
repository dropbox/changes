"""Add FileCoverage stats to model

Revision ID: 3b55ff8856f5
Revises: 15bd4b7e6622
Create Date: 2014-05-09 11:35:19.758338

"""

# revision identifiers, used by Alembic.
revision = '3b55ff8856f5'
down_revision = '15bd4b7e6622'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('filecoverage', sa.Column('diff_lines_covered', sa.Integer(), nullable=True))
    op.add_column('filecoverage', sa.Column('diff_lines_uncovered', sa.Integer(), nullable=True))
    op.add_column('filecoverage', sa.Column('lines_covered', sa.Integer(), nullable=True))
    op.add_column('filecoverage', sa.Column('lines_uncovered', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('filecoverage', 'lines_uncovered')
    op.drop_column('filecoverage', 'lines_covered')
    op.drop_column('filecoverage', 'diff_lines_uncovered')
    op.drop_column('filecoverage', 'diff_lines_covered')
