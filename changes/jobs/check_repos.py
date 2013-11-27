from datetime import datetime, timedelta
from sqlalchemy import or_

from changes.config import queue
from changes.models import Repository, RepositoryBackend


def check_repos():
    """
    Looks for any repositories which haven't checked in within several minutes
    and creates `sync_repo` tasks for them.
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=3)

    repo_list = Repository.query.filter(
        Repository.backend != RepositoryBackend.unknown,
        or_(
            Repository.last_update_attempt < cutoff,
            Repository.last_update_attempt == None,  # NOQA
        )
    )
    for repo in repo_list:
        queue.delay('sync_repo', kwargs={
            'repo_id': repo.id.hex,
        })
