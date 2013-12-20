from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import or_

from changes.config import db, queue
from changes.constants import Status, Result
from changes.models.build import Build

CHECK_BUILDS = timedelta(minutes=5)
EXPIRE_BUILDS = timedelta(hours=6)


def cleanup_builds():
    """
    Look for any jobs which haven't checked in (but are listed in a pending state)
    and mark them as finished in an unknown state.
    """
    now = datetime.utcnow()
    cutoff = now - CHECK_BUILDS

    build_list = list(Build.query.filter(
        Build.status != Status.finished,
        or_(
            Build.date_modified < cutoff,
            Build.date_modified == None,  # NOQA
        )
    ))
    if not build_list:
        return

    expired = frozenset(
        b.id for b in build_list
        if b.date_created < now - EXPIRE_BUILDS
    )
    for b_id in expired:
        current_app.logger.warn('Expiring build %s', b_id)

    db.session.query(Build).filter(
        Build.id.in_(expired),
    ).update({
        Build.date_modified: now,
        Build.status: Status.finished,
        Build.result: Result.aborted,
    }, synchronize_session=False)

    # remove expired builds
    build_ids = [
        b.id for b in build_list
        if b.id not in expired
    ]

    for build in build_list:
        db.session.expire(build)

    if not build_list:
        return

    db.session.query(Build).filter(
        Build.id.in_(build_ids),
    ).update({
        Build.date_modified: now,
    }, synchronize_session=False)

    for b_id in build_ids:
        queue.delay('sync_build', kwargs={
            'build_id': b_id.hex,
        })
