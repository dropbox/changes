from datetime import datetime
from flask import current_app
from sqlalchemy.orm import subqueryload_all

from changes.backends.base import UnrecoverableException
from changes.config import db, queue
from changes.constants import Status, Result
from changes.events import publish_job_update
from changes.models import Job, JobPlan, Plan, ItemStat, TestCase
from changes.queue.task import tracked_task
from changes.utils.agg import safe_agg


@tracked_task
def sync_job(job_id):
    job = Job.query.get(job_id)
    if not job:
        return

    if job.status == Status.finished:
        return

    # TODO(dcramer): we make an assumption that there is a single step
    job_plan = JobPlan.query.options(
        subqueryload_all('plan.steps')
    ).filter(
        JobPlan.job_id == job.id,
    ).join(Plan).first()
    try:
        if not job_plan:
            raise UnrecoverableException('Got sync_job task without job plan: %s' % (job.id,))

        try:
            step = job_plan.plan.steps[0]
        except IndexError:
            raise UnrecoverableException('Missing steps for plan')

        implementation = step.get_implementation()
        implementation.update(job=job)

    except UnrecoverableException:
        job.status = Status.finished
        job.result = Result.aborted
        current_app.logger.exception('Unrecoverable exception syncing %s', job.id)

    current_datetime = datetime.utcnow()

    job.date_modified = current_datetime

    is_finished = sync_job.verify_all_children() == Status.finished
    if is_finished:
        job.status = Status.finished

    all_phases = list(job.phases)

    job.date_started = safe_agg(
        min, (j.date_started for j in all_phases if j.date_started))

    if is_finished:
        job.date_finished = safe_agg(
            max, (j.date_finished for j in all_phases if j.date_finished))
    else:
        job.date_finished = None

    if job.date_started and job.date_finished:
        job.duration = int((job.date_finished - job.date_started).total_seconds() * 1000)
    else:
        job.duration = None

    if any(j.result is Result.failed for j in all_phases):
        job.result = Result.failed
    elif is_finished:
        job.result = safe_agg(
            max, (j.result for j in all_phases), Result.unknown)
    else:
        job.result = Result.unknown

    if is_finished:
        job.status = Status.finished
    elif any(j.status is Status.in_progress for j in all_phases):
        job.status = Status.in_progress
    else:
        job.status = Status.queued

    db.session.add(job)
    db.session.commit()

    publish_job_update(job)

    if not is_finished:
        raise sync_job.NotFinished

    # TODO(dcramer): this would make more sense as part of the xunit handler
    teststat = ItemStat(
        item_id=job.id,
        name='test_count',
        value=TestCase.query.filter(
            TestCase.job_id == job.id,
        ).count(),
    )
    db.session.add(teststat)
    db.session.commit()

    queue.delay('notify_job_finished', kwargs={
        'job_id': job.id.hex,
    })

    if job_plan:
        queue.delay('update_project_plan_stats', kwargs={
            'project_id': job.project_id.hex,
            'plan_id': job_plan.plan_id.hex,
        }, countdown=1)
