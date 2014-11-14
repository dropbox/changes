from __future__ import absolute_import, print_function

from datetime import datetime
from flask import current_app
from sqlalchemy.sql import func

from changes.backends.base import UnrecoverableException
from changes.config import db, queue
from changes.constants import Status, Result
from changes.db.utils import try_create
from changes.jobs.signals import fire_signal
from changes.models import ItemStat, Job, JobPhase, JobPlan, JobStep, TestCase
from changes.queue.task import tracked_task
from changes.utils.agg import aggregate_result, aggregate_status, safe_agg


def aggregate_job_stat(job, name, func_=func.sum):
    value = db.session.query(
        func.coalesce(func_(ItemStat.value), 0),
    ).filter(
        ItemStat.item_id.in_(
            db.session.query(JobStep.id).filter(
                JobStep.job_id == job.id,
            )
        ),
        ItemStat.name == name,
    ).as_scalar()

    try_create(ItemStat, where={
        'item_id': job.id,
        'name': name,
    }, defaults={
        'value': value
    })


def sync_job_phases(job, phases=None):
    if phases is None:
        phases = JobPhase.query.filter(JobPhase.job_id == job.id)

    for phase in phases:
        sync_phase(phase)


def sync_phase(phase):
    phase_steps = list(phase.steps)

    if phase.date_started is None:
        phase.date_started = safe_agg(min, (s.date_started for s in phase_steps))
        db.session.add(phase)

    if phase_steps:
        if all(s.status == Status.finished for s in phase_steps):
            phase.status = Status.finished
            phase.date_finished = safe_agg(max, (s.date_finished for s in phase_steps))
        else:
            # ensure we dont set the status to finished unless it actually is
            new_status = aggregate_status((s.status for s in phase_steps))
            if new_status != Status.finished:
                phase.status = new_status

        if any(s.result is Result.failed for s in phase_steps):
            phase.result = Result.failed

        elif phase.status == Status.finished:
            phase.result = aggregate_result((s.result for s in phase_steps))

    if db.session.is_modified(phase):
        phase.date_modified = datetime.utcnow()
        db.session.add(phase)
        db.session.commit()


def abort_job(task):
    job = Job.query.get(task.kwargs['job_id'])
    job.status = Status.finished
    job.result = Result.aborted
    db.session.add(job)
    db.session.flush()
    sync_job_phases(job)
    db.session.commit()
    current_app.logger.exception('Unrecoverable exception syncing job %s', job.id)


@tracked_task(on_abort=abort_job)
def sync_job(job_id):
    pass
