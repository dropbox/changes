from flask import current_app

from sqlalchemy.orm import subqueryload_all

from changes.backends.base import UnrecoverableException
from changes.constants import Status, Result
from changes.config import db
from changes.db.utils import try_create
from changes.models import (
    JobStep, JobPlan, Plan, ProjectOption, TestCase, ItemStat, FileCoverage
)
from changes.queue.task import tracked_task


def get_build_step(job_id):
    job_plan = JobPlan.query.options(
        subqueryload_all('plan.steps')
    ).filter(
        JobPlan.job_id == job_id,
    ).join(Plan).first()
    if not job_plan:
        raise UnrecoverableException('Missing job plan for job: %s' % (job_id,))

    try:
        step = job_plan.plan.steps[0]
    except IndexError:
        raise UnrecoverableException('Missing steps for plan: %s' % (job_plan.plan.id))

    implementation = step.get_implementation()
    return implementation


def abort_step(task):
    step = JobStep.query.get(task.kwargs['step_id'])
    step.status = Status.finished
    step.result = Result.aborted
    db.session.add(step)
    db.session.commit()
    current_app.logger.exception('Unrecoverable exception syncing step %s', step.id)


def is_missing_tests(step):
    query = ProjectOption.query.filter(
        ProjectOption.project_id == step.project_id,
        ProjectOption.name == 'build.expect-tests',
        ProjectOption.value == '1',
    )
    if not db.session.query(query.exists()).scalar():
        return False

    has_tests = db.session.query(TestCase.query.filter(
        TestCase.step_id == step.id,
    ).exists()).scalar()

    return not has_tests


def record_coverage_stats(step):
    # calculate lines_covered, lines_uncovered
    coverage_data = dict(db.session.query(
        FileCoverage.filename,
        FileCoverage.data,
    ).filter(
        FileCoverage.step_id == step.id,
    ))

    # TODO(dcramer): record diff coverage
    lines_covered = 0
    lines_uncovered = 0
    for filename, data in coverage_data.iteritems():
        lines_covered += data.count('C')
        lines_uncovered += data.count('U')

    try_create(ItemStat, where={
        'item_id': step.id,
        'name': 'lines_covered',
    }, defaults={
        'value': lines_covered
    })
    try_create(ItemStat, where={
        'item_id': step.id,
        'name': 'lines_uncovered',
    }, defaults={
        'value': lines_uncovered
    })


@tracked_task(on_abort=abort_step, max_retries=None)
def sync_job_step(step_id):
    step = JobStep.query.get(step_id)
    if not step:
        return

    implementation = get_build_step(step.job_id)
    implementation.update_step(step=step)

    if step.status != Status.finished:
        is_finished = False
    else:
        is_finished = sync_job_step.verify_all_children() == Status.finished

    if not is_finished:
        raise sync_job_step.NotFinished

    missing_tests = is_missing_tests(step)

    try_create(ItemStat, where={
        'item_id': step.id,
        'name': 'tests_missing',
    }, defaults={
        'value': int(missing_tests)
    })

    try:
        record_coverage_stats(step)
    except Exception:
        current_app.logger.exception('Failing recording coverage stats for step %s', step.id)

    if step.result == Result.passed and missing_tests:
        step.result = Result.failed
        db.session.add(step)
        db.session.commit()
