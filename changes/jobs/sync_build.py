from datetime import datetime
from flask import current_app
from sqlalchemy.sql import func

from changes.config import db, queue, statsreporter
from changes.constants import Result, Status
from changes.db.utils import try_create
from changes.jobs.signals import fire_signal
from changes.models import Build, ItemStat, Job
from changes.utils.agg import aggregate_result, aggregate_status, safe_agg
from changes.queue.task import tracked_task


def aggregate_build_stat(build, name, func_=func.sum):
    value = db.session.query(
        func.coalesce(func_(ItemStat.value), 0),
    ).filter(
        ItemStat.item_id.in_(
            db.session.query(Job.id).filter(
                Job.build_id == build.id,
            )
        ),
        ItemStat.name == name,
    ).as_scalar()

    try_create(ItemStat, where={
        'item_id': build.id,
        'name': name,
        'value': value,
    })


def abort_build(task):
    build = Build.query.get(task.kwargs['build_id'])
    build.status = Status.finished
    build.result = Result.aborted
    db.session.add(build)
    db.session.commit()
    current_app.logger.exception('Unrecoverable exception syncing build %s', build.id)


def _timedelta_to_millis(td):
    return int(td.total_seconds() * 1000)


@tracked_task(on_abort=abort_build)
def sync_build(build_id):
    """
    Synchronizing the build happens continuously until all jobs have reported in
    as finished or have failed/aborted.

    This task is responsible for:
    - Checking in with jobs
    - Aborting/retrying them if they're beyond limits
    - Aggregating the results from jobs into the build itself
    """
    build = Build.query.get(build_id)
    if not build:
        return

    if build.status == Status.finished:
        return

    all_jobs = list(Job.query.filter(
        Job.build_id == build_id,
    ))

    is_finished = sync_build.verify_all_children() == Status.finished
    if any(p.status != Status.finished for p in all_jobs):
        is_finished = False

    prev_started = build.date_started
    build.date_started = safe_agg(
        min, (j.date_started for j in all_jobs if j.date_started))

    # We want to report how long we waited for the build to start once and only once,
    # so we do it at the transition from not started to started.
    if not prev_started and build.date_started:
        queued_time = build.date_started - build.date_created
        statsreporter.stats().log_timing('build_start_latency', _timedelta_to_millis(queued_time))

    if is_finished:
        build.date_finished = safe_agg(
            max, (j.date_finished for j in all_jobs if j.date_finished))
    else:
        build.date_finished = None

    if build.date_started and build.date_finished:
        build.duration = _timedelta_to_millis(build.date_finished - build.date_started)
    else:
        build.duration = None

    if any(j.result is Result.failed for j in all_jobs):
        build.result = Result.failed
    elif is_finished:
        build.result = aggregate_result((j.result for j in all_jobs))
    else:
        build.result = Result.unknown

    if is_finished:
        build.status = Status.finished
    else:
        # ensure we dont set the status to finished unless it actually is
        new_status = aggregate_status((j.status for j in all_jobs))
        if new_status != Status.finished:
            build.status = new_status

    if is_finished:
        build.date_decided = datetime.utcnow()
        decided_latency = build.date_decided - build.date_finished
        statsreporter.stats().log_timing('build_decided_latency', _timedelta_to_millis(decided_latency))
    else:
        build.date_decided = None

    if db.session.is_modified(build):
        build.date_modified = datetime.utcnow()
        db.session.add(build)
        db.session.commit()

    if not is_finished:
        raise sync_build.NotFinished

    with statsreporter.stats().timer('build_stat_aggregation'):
        try:
            aggregate_build_stat(build, 'test_count')
            aggregate_build_stat(build, 'test_duration')
            aggregate_build_stat(build, 'test_failures')
            aggregate_build_stat(build, 'test_rerun_count')
            aggregate_build_stat(build, 'tests_missing')
            aggregate_build_stat(build, 'lines_covered')
            aggregate_build_stat(build, 'lines_uncovered')
            aggregate_build_stat(build, 'diff_lines_covered')
            aggregate_build_stat(build, 'diff_lines_uncovered')
        except Exception:
            current_app.logger.exception('Failing recording aggregate stats for build %s', build.id)

    fire_signal.delay(
        signal='build.finished',
        kwargs={'build_id': build.id.hex},
    )

    queue.delay('update_project_stats', kwargs={
        'project_id': build.project_id.hex,
    }, countdown=1)
