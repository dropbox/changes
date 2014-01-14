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

patchers = []


def pytest_sessionstart(session):
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


# TODO(dcramer): we should be able to use fast transaction testing here but
# that seems to be extremely difficult to abstract in sqlalchemy
def pytest_runtest_teardown(item):
    db.session.rollback()
    db.session.execute('truncate table %s' % (
        ', '.join("%s" % (t,) for t in db.metadata.sorted_tables),
    ))
    db.session.commit()
    db.session.remove()
