import logging

from changes.config import db
from changes.models import Repository, RepositoryStatus
from changes.vcs.base import CommandError, ConcurrentUpdateError


logger = logging.getLogger('update_local_repo')


def update_local_repos():
    """
    Updates repositories locally.
    """
    repo_list = list(Repository.query.filter(
        Repository.status != RepositoryStatus.inactive,
    ))

    for repo in repo_list:
        vcs = repo.get_vcs()
        # Close the read transaction to avoid a long running transaction
        db.session.commit()

        if vcs is None:
            logger.warning('Repository %s has no VCS backend set', repo.id)
            continue

        try:
            if vcs.exists():
                vcs.update()
            else:
                vcs.clone()
        except ConcurrentUpdateError:
            # The repo is already updating already. No need to update.
            pass
        except CommandError:
            logging.exception('Failed to update %s', repo.url)
