from datetime import datetime

from changes.config import db
from changes.constants import Status, Result
from changes.events import publish_build_update
from changes.models import Build, Job


def safe_agg(func, sequence):
    m = None
    for item in sequence:
        if m is None:
            m = item
        elif item:
            m = func(m, item)
    return m


def update_build_result(build_id, job_id):
    job = Job.query.get(job_id)

    # TODO(dcramer): ideally this could be an exists query, but no idea how
    # to do that
    is_finished = (Job.query.filter(
        Job.build_id == build_id,
        Job.status != Status.finished,
    ).first() is None)

    current_datetime = datetime.utcnow()

    # dont perform most work if all jobs have not finished
    if not is_finished:
        if job.result == Result.failed:
            Build.query.filter(
                Build.id == build_id
            ).update({
                Build.status: Status.in_progress,
                Build.result: Result.failed,
                Build.date_modified: current_datetime,
            }, synchronize_session=False)
        return

    all_jobs = list(Job.query.filter(
        Job.build_id == build_id,
    ))

    date_started = safe_agg(min, (j.date_started for j in all_jobs if j.date_started))
    date_finished = safe_agg(max, (j.date_finished for j in all_jobs if j.date_finished))
    if date_started and date_finished:
        duration = int((date_finished - date_started).total_seconds() * 1000)
    else:
        duration = None

    Build.query.filter(
        Build.id == build_id
    ).update({
        Build.result: max(j.result for j in all_jobs),
        Build.status: Status.finished,
        Build.date_modified: current_datetime,
        Build.date_started: date_started,
        Build.date_finished: date_finished,
        Build.duration: duration,
    }, synchronize_session=False)

    build = Build.query.get(build_id)

    publish_build_update(build)

    for job in all_jobs:
        db.session.expire(job)
