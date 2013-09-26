import os
import sys

root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if root not in sys.path:
    sys.path.insert(0, root)

from alembic.config import Config
from alembic import command

alembic_cfg = Config(os.path.join(root, 'alembic.ini'))

# force model registration
from buildbox.config import create_app, db

app, app_context, connection, transaction = None, None, None, None

from flask_sqlalchemy import _SignallingSession
from functools import partial
from sqlalchemy import orm


class SignallingSession(_SignallingSession):
    def __init__(self, db, autocommit=False, autoflush=False, **options):
        self.app = db.get_app()
        self._model_changes = {}
        bind = options.pop('bind', db.engine)
        super(_SignallingSession, self).__init__(
            autocommit=autocommit,
            autoflush=autoflush,
            bind=bind,
            binds=db.get_binds(self.app), **options)


def pytest_configure(config):
    global app, app_context, connection, transaction

    app = create_app(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='postgresql://localhost/test_buildbox',
    )
    app_context = app.test_request_context()
    app_context.push()

    assert not os.system('dropdb --if-exists test_buildbox')
    assert not os.system('createdb -E utf-8 test_buildbox')

    command.upgrade(alembic_cfg, 'head')

    db.session = db.create_scoped_session({
        'autoflush': True,
    })

    connection = db.engine.connect()
    transaction = connection.begin()


def pytest_unconfigure():
    transaction.rollback()
    connection.close()

    app_context.pop()


# TODO: mock session commands
def pytest_runtest_setup(item):
    item.__sqla_transaction = db.session.begin_nested()


def pytest_runtest_teardown(item):
    item.__sqla_transaction.rollback()
