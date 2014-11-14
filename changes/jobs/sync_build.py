from datetime import datetime
from flask import current_app
from sqlalchemy.sql import func

from changes.config import db, queue
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
    }, defaults={
        'value': value
    })


def abort_build(task):
    build = Build.query.get(task.kwargs['build_id'])
    build.status = Status.finished
    build.result = Result.aborted
    db.session.add(build)
    db.session.commit()
    current_app.logger.exception('Unrecoverable exception syncing build %s', build.id)


@tracked_task(on_abort=abort_build)
def sync_build(build_id):
    pass