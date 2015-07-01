from changes.config import db
from changes.constants import Cause, Result
from changes.models import Build, SnapshotStatus
from changes.utils.locking import lock


@lock
def build_finished_handler(build_id, **kwargs):
    build = Build.query.get(build_id)

    # only handle snapshot builds
    if build is None or build.cause != Cause.snapshot:
        return

    # If the snapshot build did not pass then we guarantee that
    # the snapshot is either invalidated or is failed.
    if build.result != Result.passed and build.snapshot is not None:
        if build.snapshot.status == SnapshotStatus.active:
            build.snapshot.status = SnapshotStatus.invalidated
        else:
            build.snapshot.status = SnapshotStatus.failed
        db.session.commit()
