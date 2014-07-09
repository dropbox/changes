from __future__ import absolute_import, print_function

from datetime import datetime
from flask import current_app
from sqlalchemy.orm import subqueryload_all
from sqlalchemy.sql import func

from changes.backends.base import UnrecoverableException
from changes.config import db, queue
from changes.constants import Status, Result
from changes.db.utils import try_create
from changes.jobs.signals import fire_signal
from changes.models import (
    FailureReason, ItemOption, ItemStat, Job, JobPhase, JobPlan, JobStep, Plan,
    TestCase
)
from changes.queue.task import tracked_task
from changes.utils.agg import safe_agg


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


def has_timed_out(job, job_plan):
    if job.status != Status.in_progress:
        return False

    if not job.date_started:
        return False

    options = dict(
        db.session.query(
            ItemOption.name, ItemOption.value
        ).filter(
            ItemOption.item_id == job_plan.plan_id,
            ItemOption.name.in_([
                'build.timeout',
            ])
        )
    )

    timeout = int(options.get('build.timeout') or 0)
    if not timeout:
        return False

    # timeout is in minutes
    timeout = timeout * 60

    delta = datetime.utcnow() - job.date_started
    if delta.total_seconds() > timeout:
        return True

    return False


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

    if all(s.status == Status.finished for s in phase_steps):
        phase.status = Status.finished
        phase.date_finished = safe_agg(max, (s.date_finished for s in phase_steps))

    elif any(s.status != Status.finished for s in phase_steps):
        phase.status = Status.in_progress
        db.session.add(phase)

    if any(s.result is Result.failed for s in phase_steps):
        phase.result = Result.failed

    elif phase.status == Status.finished:
        phase.result = safe_agg(max, (s.result for s in phase.steps), Result.unknown)

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

        if has_timed_out(job, job_plan):
            remaining_steps = list(JobStep.query.filter(
                JobStep.status != Status.finished,
                JobStep.job_id == job.id,
            ))

            implementation.cancel(job=job)

            for step in remaining_steps:
                step.result = Result.failed
                step.status = Status.finished
                db.session.add(step)

                try_create(FailureReason, {
                    'step_id': step.id,
                    'job_id': job.id,
                    'build_id': job.build_id,
                    'project_id': job.project_id,
                    'reason': 'timeout'
                })

            # ensure the job result actually reflects a failure
            job.result = Result.failed
            job.status = Status.finished
            db.session.add(job)
        else:
            implementation.update(job=job)

    except UnrecoverableException:
        job.status = Status.finished
        job.result = Result.aborted
        current_app.logger.exception('Unrecoverable exception syncing %s', job.id)

    is_finished = sync_job.verify_all_children() == Status.finished
    if is_finished:
        job.status = Status.finished

    db.session.flush()

    all_phases = list(job.phases)

    # propagate changes to any phases as they live outside of the
    # normalize synchronization routines
    sync_job_phases(job, all_phases)

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

    # if any phases are marked as failing, fail the build
    if any(j.result is Result.failed for j in all_phases):
        job.result = Result.failed
    # if any test cases were marked as failing, fail the build
    elif TestCase.query.filter(TestCase.result == Result.failed, TestCase.job_id == job.id).first():
        job.result = Result.failed
    # if we've finished all phases, use the best result available
    elif is_finished:
        job.result = safe_agg(
            max, (j.result for j in all_phases), Result.unknown)
    else:
        job.result = Result.unknown

    if is_finished:
        job.status = Status.finished
    elif any(j.status is not Status.queued for j in all_phases):
        job.status = Status.in_progress
    else:
        job.status = Status.queued

    if db.session.is_modified(job):
        job.date_modified = datetime.utcnow()

        db.session.add(job)
        db.session.commit()

    if not is_finished:
        raise sync_job.NotFinished

    try:
        aggregate_job_stat(job, 'test_count')
        aggregate_job_stat(job, 'test_duration')
        aggregate_job_stat(job, 'test_failures')
        aggregate_job_stat(job, 'test_rerun_count')
        aggregate_job_stat(job, 'tests_missing')
        aggregate_job_stat(job, 'lines_covered')
        aggregate_job_stat(job, 'lines_uncovered')
        aggregate_job_stat(job, 'diff_lines_covered')
        aggregate_job_stat(job, 'diff_lines_uncovered')
    except Exception:
        current_app.logger.exception('Failing recording aggregate stats for job %s', job.id)

    fire_signal.delay(
        signal='job.finished',
        kwargs={'job_id': job.id.hex},
    )

    if job_plan:
        queue.delay('update_project_plan_stats', kwargs={
            'project_id': job.project_id.hex,
            'plan_id': job_plan.plan_id.hex,
        }, countdown=1)
