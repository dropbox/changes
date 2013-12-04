from datetime import datetime, timedelta

from changes.config import queue
from changes.constants import Status
from changes.models.build import Build


def cleanup_builds():
    """
    Look for any jobs which haven't checked in (but are listed in a pending state)
    and mark them as finished in an unknown state.
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=5)

    build_list = Build.query.filter(
        Build.status != Status.finished,
        Build.date_modified < cutoff,
    )
    for build in build_list:
        queue.delay('sync_build', kwargs={
            'build_id': build.id.hex,
        })
