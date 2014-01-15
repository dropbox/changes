import os
import pytest
import sys

root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if root not in sys.path:
    sys.path.insert(0, root)

from alembic.config import Config
from alembic import command
from sqlalchemy import event
from sqlalchemy.orm import Session

alembic_cfg = Config(os.path.join(root, 'alembic.ini'))

from changes.config import create_app, db


@pytest.fixture(scope='session')
def app(request):
    app = create_app(
        _read_config=False,
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='postgresql:///test_changes',
        REDIS_URL='redis://localhost/9',
        BASE_URI='http://example.com',
        REPO_ROOT='/tmp',
        JENKINS_SYNC_LOG_ARTIFACTS=True,
        GOOGLE_CLIENT_ID='a' * 12,
        GOOGLE_CLIENT_SECRET='b' * 40,
    )
    app_context = app.test_request_context()
    app_context.push()
    return app


@pytest.fixture(scope='session', autouse=True)
def setup_db(request, app):
    # 9.1 does not support --if-exists
    if os.system("psql -l | grep 'test_changes'") == 0:
        assert not os.system('dropdb test_changes')
    assert not os.system('createdb -E utf-8 test_changes')

    command.upgrade(alembic_cfg, 'head')

    @event.listens_for(Session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()


@pytest.fixture(autouse=True)
def dbsession(request):
    request.addfinalizer(db.session.remove)

    db.session.begin_nested()
