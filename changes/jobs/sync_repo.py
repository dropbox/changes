from datetime import datetime
from flask import current_app

from changes.config import db, queue
from changes.models import Repository


def sync_repo(repo_id):
    repo = Repository.query.get(repo_id)
    if not repo:
        return

    vcs = repo.get_vcs()
    if vcs is None:
        return

    repo.last_update_attempt = datetime.utcnow()
    db.session.add(repo)

    try:
        if vcs.exists():
            vcs.update()
        else:
            vcs.clone()

        # TODO(dcramer): this doesnt scrape everything, and really we wouldn't
        # want to do this all in a single job so we should split this into a
        # backfill task
        might_have_more = True
        parent = None
        while might_have_more:
            might_have_more = False
            for commit in vcs.log(parent=parent):
                revision, created = commit.save(repo)
                if not created:
                    break
                might_have_more = True
                parent = commit.id

        repo.last_update = datetime.utcnow()

        db.session.add(repo)

        queue.delay('sync_repo', kwargs={
            'repo_id': repo_id
        }, countdown=15)

    except Exception as exc:
        # should we actually use retry support here?
        current_app.logger.exception('Failed to sync repository %s', repo_id)
        raise queue.retry('sync_repo', kwargs={
            'repo_id': repo_id,
        }, exc=exc, countdown=120)
