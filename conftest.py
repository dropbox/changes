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
from changes.storage.mock import FileStorageCache


@pytest.fixture(scope='session')
def session_config(request):
    db_name = 'test_changes'

    return {
        'db_name': db_name,
        # TODO(dcramer): redis db is shared
        'redis_db': '9',
    }


@pytest.fixture(scope='session')
def app(request, session_config):
    app = create_app(
        _read_config=False,
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='postgresql:///' + session_config['db_name'],
        REDIS_URL='redis://localhost/' + session_config['redis_db'],
        BASE_URI='http://example.com',
        REPO_ROOT='/tmp',
        GREEN_BUILD_URL='https://foo.example.com',
        GREEN_BUILD_AUTH=('username', 'password'),
        JENKINS_URL='http://jenkins.example.com',
        PHABRICATOR_LINK_HOST='http://phabricator.example.com',
        PHABRICATOR_API_HOST='http://phabricator.example.com',
        GOOGLE_CLIENT_ID='a' * 12,
        GOOGLE_CLIENT_SECRET='b' * 40,
        DEFAULT_FILE_STORAGE='changes.storage.mock.FileStorageCache',
        LXC_PRE_LAUNCH='echo pre',
        LXC_POST_LAUNCH='echo post',
        SNAPSHOT_S3_BUCKET='snapshot-bucket'
    )
    app_context = app.test_request_context()
    context = app_context.push()

    # request.addfinalizer(app_context.pop)
    return app


@pytest.fixture(scope='session', autouse=True)
def setup_db(request, app, session_config):
    db_name = session_config['db_name']
    # 9.1 does not support --if-exists
    if os.system("psql -l | grep '%s'" % db_name) == 0:
        assert not os.system('dropdb %s' % db_name)
    assert not os.system('createdb -E utf-8 %s' % db_name)

    command.upgrade(alembic_cfg, 'head')

    @event.listens_for(Session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()

    # TODO: find a way to kill db connections so we can dropdob
    # def teardown():
    #     os.system('dropdb %s' % db_name)

    # request.addfinalizer(teardown)


@pytest.fixture(autouse=True)
def db_session(request):
    request.addfinalizer(db.session.remove)

    db.session.begin_nested()


@pytest.fixture(autouse=True)
def redis_session(request, app):
    import redis
    conn = redis.from_url(app.config['REDIS_URL'])
    conn.flushdb()


def pytest_runtest_setup(item):
    FileStorageCache.clear()
