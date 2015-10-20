import logging

from changes.vcs.base import CommandError
from changes.models import Repository, RepositoryStatus


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
        if vcs is None:
            logger.warning('Repository %s has no VCS backend set', repo.id)
            continue

        try:
            if vcs.exists():
                vcs.update()
            else:
                vcs.clone()
        except CommandError:
            logging.exception('Failed to update %s', repo.url)
