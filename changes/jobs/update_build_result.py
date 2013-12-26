from datetime import datetime

from changes.config import db
from changes.constants import Status, Result
from changes.models import Build, Job


def update_build_result(build_id, job_id):
    job = Job.query.get(job_id)

    is_finished = not Job.query.filter(
        Job.build_id == build_id,
        Job.status != Status.finished,
    ).exists()

    current_datetime = datetime.utcnow()

    # dont perform most work if all jobs have not finished
    if not is_finished:
        if job.result == Result.failed:
            Build.query.filter(
                Build.id == build_id
            ).update({
                Build.result: Result.failed,
                Build.date_modified: current_datetime,
            }, synchronize_session=False)
        return

    all_jobs = list(Job.query.filter(
        Job.build_id == build_id,
    ))

    Build.query.filter(
        Build.id == build_id
    ).update({
        Build.result: max(j.result for j in all_jobs),
        Build.status: Status.finished,
        Build.duration: sum(j.duration for j in all_jobs),
        Build.date_started: min(j.date_started for j in all_jobs),
        Build.date_modified: current_datetime,
        Build.date_finished: max(j.date_finished for j in all_jobs),
    }, synchronize_session=False)

    for job in all_jobs:
        db.session.expire(job)
