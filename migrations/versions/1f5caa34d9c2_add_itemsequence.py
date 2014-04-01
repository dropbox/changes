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
CREATE OR REPLACE FUNCTION next_item_value(uuid) RETURNS bigint AS $$
DECLARE
    cur_parent_id ALIAS FOR $1;
    next_value int;
BEGIN
    next_value := value FROM itemsequence WHERE parent_id = cur_parent_id FOR UPDATE;
    IF next_value IS NULL THEN
        next_value := 0;
        BEGIN
            INSERT INTO itemsequence (parent_id, value) VALUES (cur_parent_id, next_value + 1);
            RETURN next_value + 1;
        EXCEPTION WHEN unique_violation THEN
            next_value := value FROM itemsequence WHERE parent_id = cur_parent_id FOR UPDATE;
        END;
    END IF;

    UPDATE itemsequence SET value = value + 1 WHERE parent_id = cur_parent_id;
    RETURN next_value + 1;
END
$$ LANGUAGE plpgsql
"""


def upgrade():
    op.create_table('itemsequence',
        sa.Column('parent_id', sa.GUID(), nullable=False),
        sa.Column('value', sa.Integer(), server_default='1', nullable=False),
        sa.PrimaryKeyConstraint('parent_id', 'value')
    )
    op.execute(NEXT_ITEM_VALUE_FUNCTION)


def downgrade():
    op.drop_table('itemsequence')
    op.execute('DROP FUNCTION IF EXISTS next_item_value(uuid)')
