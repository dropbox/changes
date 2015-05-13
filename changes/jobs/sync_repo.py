from __future__ import absolute_import, print_function

import logging

from datetime import datetime

from changes.config import db
from changes.jobs.signals import fire_signal
from changes.models import Repository, RepositoryStatus
from changes.queue.task import tracked_task

logger = logging.getLogger('repo.sync')


@tracked_task(max_retries=None)
def sync_repo(repo_id, continuous=True):
    """
    Polls repositories for new commits, and fires signals for revisions.
    """
    repo = Repository.query.get(repo_id)
    if not repo:
        logger.error('Repository %s not found', repo_id)
        return

    vcs = repo.get_vcs()
    if vcs is None:
        logger.warning('Repository %s has no VCS backend set', repo.id)
        return

    if repo.status != RepositoryStatus.active:
        logger.info('Repository %s is not active', repo.id)
        return

    Repository.query.filter(
        Repository.id == repo.id,
    ).update({
        'last_update_attempt': datetime.utcnow(),
    }, synchronize_session=False)
    db.session.commit()

    if vcs.exists():
        vcs.update()
    else:
        vcs.clone()

    # TODO(dcramer): this doesnt scrape everything, and really we wouldn't
    # want to do this all in a single job so we should split this into a
    # backfill task
    # TODO(dcramer): this doesn't collect commits in non-default branches
    might_have_more = True
    parent = None
    while might_have_more:
        might_have_more = False
        for commit in vcs.log(parent=parent):
            revision, created = commit.save(repo)
            db.session.commit()
            if not created:
                break

            might_have_more = True
            parent = commit.id

            fire_signal.delay(
                signal='revision.created',
                kwargs={'repository_id': repo.id.hex,
                        'revision_sha': revision.sha},
            )

    Repository.query.filter(
        Repository.id == repo.id,
    ).update({
        'last_update': datetime.utcnow(),
    }, synchronize_session=False)
    db.session.commit()

    if continuous:
        raise sync_repo.NotFinished
