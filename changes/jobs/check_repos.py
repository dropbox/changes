from datetime import datetime, timedelta
from sqlalchemy import or_

from changes.config import db
from changes.config import queue
from changes.models import Repository, RepositoryBackend


def check_repos():
    """
    Looks for any repositories which haven't checked in within several minutes
    and creates `sync_repo` tasks for them.
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=5)

    repo_list = list(Repository.query.filter(
        Repository.backend != RepositoryBackend.unknown,
        or_(
            Repository.last_update_attempt < cutoff,
            Repository.last_update_attempt == None,  # NOQA
        )
    ))
    if not repo_list:
        return

    db.session.query(Repository).filter(
        Repository.id.in_([r.id for r in repo_list]),
    ).update({
        Repository.last_update_attempt: now,
    }, synchronize_session=False)

    for repo in repo_list:
        queue.delay('sync_repo', kwargs={
            'repo_id': repo.id.hex,
        })
