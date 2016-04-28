from changes.jobs.sync_repo import sync_repo
from changes.models.repository import Repository, RepositoryBackend


def check_repos():
    """
    Looks for any repositories which haven't checked in within several minutes
    and creates `sync_repo` tasks for them.
    """
    repo_list = list(Repository.query.filter(
        Repository.backend != RepositoryBackend.unknown,
    ))

    for repo in repo_list:
        sync_repo.delay_if_needed(
            task_id=repo.id.hex,
            repo_id=repo.id.hex,
        )
