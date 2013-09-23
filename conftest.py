import os
import sys

root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if root not in sys.path:
    sys.path.insert(0, root)

from alembic.config import Config
from alembic import command

alembic_cfg = Config(os.path.join(root, 'alembic.ini'))

# force model registration
from buildbox.conf import settings
from buildbox.db.backend import Backend

engine, connection, transaction = None, None, None


def pytest_configure(config):
    global transaction, connection, engine

    settings['database'] = 'postgresql:///test_buildbox'

    assert not os.system('dropdb --if-exists test_buildbox')
    assert not os.system('createdb -E utf-8 test_buildbox')

    command.upgrade(alembic_cfg, 'head')

    engine = Backend.instance().engine
    connection = engine.connect()
    transaction = connection.begin()


def pytest_unconfigure():
    global transaction, connection, engine

    transaction.rollback()
    connection.close()
    engine.dispose()


def pytest_runtest_setup(item):
    global connection

    item.__sqla_transaction = connection.begin_nested()


def pytest_runtest_teardown(item):
    item.__sqla_transaction.rollback()
