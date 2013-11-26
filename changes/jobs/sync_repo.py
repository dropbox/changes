import os.path

from datetime import datetime
from flask import current_app

from changes.config import db, queue
from changes.vcs.git import GitVcs
from changes.vcs.hg import MercurialVcs
from changes.models import Repository, RepositoryBackend


def get_vcs(repo):
    kwargs = {
        'path': os.path.join(current_app.config['REPO_ROOT'], repo.id.hex),
        'url': repo.url,
    }

    if repo.backend == RepositoryBackend.git:
        return GitVcs(**kwargs)
    elif repo.backend == RepositoryBackend.hg:
        return MercurialVcs(**kwargs)
    else:
        return None


def sync_repo(repo_id):
    repo = Repository.query.get(repo_id)
    if not repo:
        return

    vcs = get_vcs(repo)
    if vcs is None:
        return

    repo.last_update_attempt = datetime.utcnow()
    db.session.add(repo)
    db.session.commit()

    try:
        if vcs.exists():
            vcs.update()
        else:
            vcs.clone()
        repo.last_update = datetime.utcnow()

        db.session.add(repo)
        db.session.commit()

        queue.delay('sync_repo', kwargs={
            'repo_id': repo_id
        }, countdown=15)

    except Exception as exc:
        # should we actually use retry support here?
        raise queue.retry('sync_repo', kwargs={
            'repo_id': repo_id,
        }, exc=exc, countdown=120)
