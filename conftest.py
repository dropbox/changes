import mock
import os
import sys

root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if root not in sys.path:
    sys.path.insert(0, root)

from alembic.config import Config
from alembic import command

alembic_cfg = Config(os.path.join(root, 'alembic.ini'))

# force model registration
from changes.config import create_app, db

app, app_context, connection, transaction, patchers = None, None, None, None, []

from flask_sqlalchemy import _SignallingSession


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


def pytest_sessionstart(session):
    global app, app_context, connection, transaction, patchers

    app = create_app(
        _read_config=False,
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='postgresql:///test_changes',
        REDIS_URL='redis://localhost/9',
        BASE_URI='http://example.com',
        REPO_ROOT='/tmp',
        JENKINS_SYNC_LOG_ARTIFACTS=True,
    )
    app_context = app.test_request_context()
    app_context.push()
    # 9.1 does not support --if-exists
    if os.system("psql -l | grep 'test_changes'") == 0:
        assert not os.system('dropdb test_changes')
    assert not os.system('createdb -E utf-8 test_changes')

    command.upgrade(alembic_cfg, 'head')

    db.session = db.create_scoped_session({
        'autoflush': True,
        'autocommit': True,
    })


# TODO: mock session commands
def pytest_runtest_setup(item):
    item.__sqla_transaction = db.session.begin()
    patchers.extend([
        mock.patch.object(db.session, 'commit'),
        mock.patch.object(db.session, 'rollback'),
        # TODO(dcramer): if we correctly mocked out commit to only allow
        # savepoint commits we wouldn't need to mock begin_nested
        # mock.patch.object(db.session, 'begin_nested'),
    ])
    for p in patchers:
        p.start()


def pytest_runtest_teardown(item):
    item.__sqla_transaction.rollback()
    while patchers:
        patchers.pop().stop()
