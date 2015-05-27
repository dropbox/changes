"""add label_sha index

Revision ID: 2f12902f7f55
Revises: 1c537486cef7
Create Date: 2015-05-26 09:33:50.930456

"""

# revision identifiers, used by Alembic.
revision = '2f12902f7f55'
down_revision = '1c537486cef7'

from alembic import op
import psycopg2
import sqlalchemy as sa


def upgrade():
    '''
    We need to set isolation level to make the concurrent query run outside other transaction
    blocks. If we don't do it, we will get an error: 'sqlalchemy.exc.InternalError:
    (psycopg2.InternalError) <query> cannot run inside a transaction block'

    At some point, when our SQLAlchemy gets updated to a version >= 0.9.9, we will be able to just
    do op.create_index with postgresql_concurrently=True.
    '''
    query = "CREATE INDEX CONCURRENTLY idx_test_label_sha ON test (label_sha)"
    connection = op.get_bind()
    connection.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    connection.execute(sa.sql.text(query))
    connection.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)

def downgrade():
    query = "DROP INDEX CONCURRENTLY idx_test_label_sha"
    connection = op.get_bind()
    connection.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    connection.execute(sa.sql.text(query))
    connection.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
