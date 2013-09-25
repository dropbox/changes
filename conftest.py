import os
import sys

root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if root not in sys.path:
    sys.path.insert(0, root)

from alembic.config import Config
from alembic import command

alembic_cfg = Config(os.path.join(root, 'alembic.ini'))

# force model registration
from buildbox.app import db
from buildbox.config import settings

transaction = None


def pytest_configure(config):
    global transaction

    settings['database'] = 'postgresql://localhost/test_buildbox'

    assert not os.system('dropdb --if-exists test_buildbox')
    assert not os.system('createdb -E utf-8 test_buildbox')

    command.upgrade(alembic_cfg, 'head')

    transaction = db.connection.begin()


def pytest_unconfigure():
    global transaction

    transaction.rollback()
    db.connection.close()


def pytest_runtest_setup(item):
    global backend

    item.__sqla_transaction = db.connection.begin_nested()


def pytest_runtest_teardown(item):
    item.__sqla_transaction.rollback()
