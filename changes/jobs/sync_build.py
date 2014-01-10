from datetime import datetime
from flask import current_app

from changes.config import db, queue
from changes.constants import Result, Status
from changes.events import publish_build_update
from changes.models import Build, Job, Task
from changes.utils.agg import safe_agg
from changes.utils.locking import lock


@lock
def sync_build(build_id):
    """
    Synchronizing the build happens continuously until all jobs have reported in
    as finished or have failed/aborted.

    This task is responsible for:
    - Checking in with jobs
    - Aborting/retrying them if they're beyond limits
    - Aggregating the results from jobs into the build itself
    """
    try:
        _sync_build(build_id)

    except Exception:
        # Ensure we continue to synchronize this job as this could be a
        # temporary failure
        current_app.logger.exception('Failed to sync build %s', build_id)
        raise queue.retry('sync_build', kwargs={
            'build_id': build_id,
        }, countdown=60)


def _sync_build(build_id):
    # TODO(dcramer): sync_build should be responsible for requeueing sync_job
    # tasks that haven't checked in
    build = Build.query.get(build_id)
    if not build:
        return

    if build.status == Status.finished:
        return

    is_finished = Task.check('sync_job', build.id) == Status.finished

    current_datetime = datetime.utcnow()

    all_jobs = list(Job.query.filter(
        Job.build_id == build_id,
    ))

    date_started = safe_agg(
        min, (j.date_started for j in all_jobs if j.date_started))

    if is_finished:
        date_finished = safe_agg(
            max, (j.date_finished for j in all_jobs if j.date_finished))
    else:
        date_finished = None

    if date_started and date_finished:
        duration = int((date_finished - date_started).total_seconds() * 1000)
    else:
        duration = None

    if any(j.result is Result.failed for j in all_jobs):
        result = Result.failed
    elif is_finished:
        result = safe_agg(
            max, (j.result for j in all_jobs), Result.unknown)
    else:
        result = Result.unknown

    if is_finished:
        status = Status.finished
    elif any(j.status is Status.in_progress for j in all_jobs):
        status = Status.in_progress
    else:
        status = Status.queued

    Build.query.filter(
        Build.id == build_id
    ).update({
        Build.result: result,
        Build.status: status,
        Build.date_modified: current_datetime,
        Build.date_started: date_started,
        Build.date_finished: date_finished,
        Build.duration: duration,
    }, synchronize_session=False)

    build = Build.query.get(build_id)

    publish_build_update(build)

    if is_finished:
        queue.delay('update_project_stats', kwargs={
            'project_id': build.project_id.hex,
        }, countdown=1)

    else:
        queue.delay('sync_build', kwargs={
            'build_id': build.id.hex,
        }, countdown=5)

    for job in all_jobs:
        db.session.expire(job)
    db.session.expire(build)
