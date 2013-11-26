from datetime import datetime, timedelta

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
        Repository.last_update_attempt < cutoff,
    )
    for repo in repo_list:
        queue.delay('sync_repo', kwargs={
            'repo_id': repo.id.hex,
        })
