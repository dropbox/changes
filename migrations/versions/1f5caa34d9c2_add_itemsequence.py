"""Add ItemSequence

Revision ID: 1f5caa34d9c2
Revises: bb141e41aab
Create Date: 2014-03-31 22:44:32.721446

"""

# revision identifiers, used by Alembic.
revision = '1f5caa34d9c2'
down_revision = 'bb141e41aab'

from alembic import op
import sqlalchemy as sa


NEXT_ITEM_VALUE_FUNCTION = """
CREATE OR REPLACE FUNCTION next_item_value(uuid) RETURNS int AS $$
DECLARE
  cur_parent_id ALIAS FOR $1;
  next_value int;
BEGIN
  LOOP
    UPDATE itemsequence SET value = value + 1 WHERE parent_id = cur_parent_id
    RETURNING value INTO next_value;
    IF FOUND THEN
      RETURN next_value;
    END IF;

    BEGIN
        INSERT INTO itemsequence (parent_id, value) VALUES (cur_parent_id, 1)
        RETURNING value INTO next_value;
        RETURN next_value;
    EXCEPTION WHEN unique_violation THEN
        -- do nothing
    END;
  END LOOP;
END;
$$ LANGUAGE plpgsql
"""

ADD_BUILD_SEQUENCES = """
INSERT INTO itemsequence (parent_id, value)
SELECT project_id, max(number) FROM build GROUP BY project_id
"""

ADD_JOB_SEQUENCES = """
INSERT INTO itemsequence (parent_id, value)
SELECT build_id, count(*) FROM job WHERE build_id IS NOT NULL GROUP BY build_id
"""


def upgrade():
    op.create_table('itemsequence',
        sa.Column('parent_id', sa.GUID(), nullable=False),
        sa.Column('value', sa.Integer(), server_default='1', nullable=False),
        sa.PrimaryKeyConstraint('parent_id', 'value')
    )
    op.execute(NEXT_ITEM_VALUE_FUNCTION)
    op.execute(ADD_BUILD_SEQUENCES)
    op.execute(ADD_JOB_SEQUENCES)


def downgrade():
    op.drop_table('itemsequence')
    op.execute('DROP FUNCTION IF EXISTS next_item_value(uuid)')
