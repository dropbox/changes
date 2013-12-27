from datetime import datetime

from changes.config import db
from changes.constants import Status, Result
from changes.events import publish_build_update
from changes.models import Build, Job


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

    date_started = min(j.date_started for j in all_jobs)
    date_finished = max(j.date_finished for j in all_jobs)
    duration = int((date_finished - date_started).total_seconds() * 1000)

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
