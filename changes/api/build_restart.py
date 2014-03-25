from sqlalchemy.orm import joinedload

from datetime import datetime

from changes.api.base import APIView
from changes.api.build_index import execute_build
from changes.config import db
from changes.constants import Result, Status
from changes.models import Build, Job, ItemStat


class BuildRestartAPIView(APIView):
    def post(self, build_id):
        build = Build.query.options(
            joinedload('project', innerjoin=True),
            joinedload('author'),
            joinedload('source'),
        ).get(build_id)
        if build is None:
            return '', 404

        if build.status != Status.finished:
            return '', 400

        # remove any existing job data
        # TODO(dcramer): this is potentially fairly slow with cascades
        Job.query.filter(
            Job.build == build
        ).delete()

        ItemStat.query.filter(
            ItemStat.item_id == build.id
        ).delete()

        build.date_started = datetime.utcnow()
        build.date_modified = build.date_started
        build.date_finished = None
        build.duration = None
        build.status = Status.queued
        build.result = Result.unknown
        db.session.add(build)

        execute_build(build=build)

        return self.respond(build)
