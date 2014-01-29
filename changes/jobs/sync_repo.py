from datetime import datetime

from changes.config import db
from changes.models import Repository
from changes.queue.task import tracked_task


@tracked_task
def sync_repo(repo_id, continuous=True):
    repo = Repository.query.get(repo_id)
    if not repo:
        return

    vcs = repo.get_vcs()
    if vcs is None:
        return

    repo.last_update_attempt = datetime.utcnow()
    db.session.add(repo)
    db.session.commit()

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
            db.session.commit()
            if not created:
                break
            might_have_more = True
            parent = commit.id

    repo.last_update = datetime.utcnow()

    db.session.add(repo)
    db.session.commit()

    if continuous:
        raise sync_repo.NotFinished
