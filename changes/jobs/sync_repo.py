from __future__ import absolute_import, print_function

import logging

from datetime import datetime

from changes.config import db
from changes.jobs.signals import fire_signal
from changes.models import Repository, RepositoryStatus, Revision
from changes.queue.task import tracked_task
from changes.vcs.base import ConcurrentUpdateError

logger = logging.getLogger('repo.sync')

NUM_RECENT_COMMITS = 30


@tracked_task(max_retries=None)
def sync_repo(repo_id, continuous=True):
    repo = Repository.query.get(repo_id)
    if not repo:
        logger.error('Repository %s not found', repo_id)
        return False

    if sync(repo) and continuous:
        raise sync_repo.NotFinished(retry_after=20)


def sync(repo):
    """
    Checks the repository for new commits, and fires revision.created signals.
    """
    vcs = repo.get_vcs()
    if vcs is None:
        logger.warning('Repository %s has no VCS backend set', repo.id)
        return False

    if repo.status != RepositoryStatus.active:
        logger.info('Repository %s is not active', repo.id)
        return False

    Repository.query.filter(
        Repository.id == repo.id,
    ).update({
        'last_update_attempt': datetime.utcnow(),
    }, synchronize_session=False)
    db.session.commit()

    if vcs.exists():
        try:
            vcs.update()
        except ConcurrentUpdateError:
            # Updating already so no need to update.
            pass
    else:
        vcs.clone()

    # The loop below do two things:
    # 1) adds new revisions to the database
    # 2) fire off revision created signals for recent revisions
    #
    # TODO(dcramer): this doesnt scrape everything, and really we wouldn't
    # want to do this all in a single job so we should split this into a
    # backfill task
    for commit in vcs.log(parent=None, limit=NUM_RECENT_COMMITS, first_parent=False):
        known_revision = Revision.query.filter(
            Revision.repository_id == repo.id,
            Revision.sha == commit.id
        ).with_for_update().scalar()

        if known_revision and known_revision.date_created_signal:
            db.session.commit()
            continue

        revision, created, _ = commit.save(repo)
        db.session.commit()

        # Lock the revision.
        revision = Revision.query.filter(
            Revision.repository_id == repo.id,
            Revision.sha == commit.id
        ).with_for_update().scalar()

        # Fire the signal if the revision was created or its branches were discovered.
        #
        # The `revision.branches` check is a hack right now to prevent builds from
        # triggering on branchless commits.
        if revision.branches and not revision.date_created_signal:
            revision.date_created_signal = datetime.utcnow()
            fire_signal.delay(
                signal='revision.created',
                kwargs={'repository_id': repo.id.hex,
                        'revision_sha': revision.sha},
            )
            db.session.commit()
        db.session.commit()

    Repository.query.filter(
        Repository.id == repo.id,
    ).update({
        'last_update': datetime.utcnow(),
    }, synchronize_session=False)
    db.session.commit()

    return True
