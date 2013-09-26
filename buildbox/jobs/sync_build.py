from flask import current_app as app

from buildbox.backends.koality.backend import KoalityBackend
from buildbox.config import queue, db
from buildbox.constants import Status
from buildbox.models.build import Build


@queue.job
def sync_build(build_id):
    build = Build.query.get(build_id)

    backend = KoalityBackend(
        app=app,
        base_url=app.config['KOALITY_URL'],
        api_key=app.config['KOALITY_API_KEY'],
    )
    build, _ = backend.sync_build_details(
        build=build,
    )
    db.session.commit()

    if build.status != Status.finished:
        print build.id, build.status
        sync_build.delay(
            build_id=build.id,
        )
