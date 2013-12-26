from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import or_

from changes.config import db, queue
from changes.constants import Status, Result
from changes.models import Job

CHECK_BUILDS = timedelta(minutes=5)
EXPIRE_BUILDS = timedelta(hours=6)


def cleanup_jobs():
    """
    Look for any jobs which haven't checked in (but are listed in a pending state)
    and mark them as finished in an unknown state.
    """
    now = datetime.utcnow()
    cutoff = now - CHECK_BUILDS

    job_list = list(Job.query.filter(
        Job.status != Status.finished,
        or_(
            Job.date_modified < cutoff,
            Job.date_modified == None,  # NOQA
        )
    ))
    if not job_list:
        return

    expired = frozenset(
        b.id for b in job_list
        if b.date_created < now - EXPIRE_BUILDS
    )
    for b_id in expired:
        current_app.logger.warn('Expiring job %s', b_id)

    db.session.query(Job).filter(
        Job.id.in_(expired),
    ).update({
        Job.date_modified: now,
        Job.status: Status.finished,
        Job.result: Result.aborted,
    }, synchronize_session=False)

    # remove expired jobs
    job_ids = [
        b.id for b in job_list
        if b.id not in expired
    ]

    for job in job_list:
        db.session.expire(job)

    if not job_list:
        return

    db.session.query(Job).filter(
        Job.id.in_(job_ids),
    ).update({
        Job.date_modified: now,
    }, synchronize_session=False)

    for b_id in job_ids:
        queue.delay('sync_job', kwargs={
            'job_id': b_id.hex,
        })
