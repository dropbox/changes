from flask import current_app as app

from changes.backends.koality.builder import KoalityBuilder
from changes.config import queue, db
from changes.constants import Status
from changes.models.build import Build


@queue.job
def sync_build(build_id):
    try:
        build = Build.query.get(build_id)
        if build.status == Status.finished:
            return

        backend = KoalityBuilder(
            app=app,
            base_url=app.config['KOALITY_URL'],
            api_key=app.config['KOALITY_API_KEY'],
        )
        build, _ = backend.sync_build_details(
            build=build,
        )
        db.session.commit()

        if build.status != Status.finished:
            sync_build.delay(
                build_id=build.id,
            )
    except Exception:
        sync_build.delay(
            build_id=build.id,
        )
        raise
