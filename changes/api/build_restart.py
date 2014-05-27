from sqlalchemy.orm import joinedload

from datetime import datetime

from changes.api.base import APIView
from changes.api.build_index import execute_build
from changes.config import db
from changes.constants import Result, Status
from changes.models import Build, Job, JobStep, ItemStat


class BuildRestartAPIView(APIView):
    def post(self, build_id):
        build = Build.query.options(
            joinedload('project', innerjoin=True),
            joinedload('author'),
            joinedload('source').joinedload('revision'),
        ).get(build_id)
        if build is None:
            return '', 404

        if build.status != Status.finished:
            return '', 400

        # ItemStat doesnt cascade by itself
        stat_ids = [build.id]
        job_ids = [
            j[0] for j in
            db.session.query(Job.id).filter(Job.build_id == build.id)
        ]
        if job_ids:
            step_ids = [
                s[0] for s in
                db.session.query(JobStep.id).filter(JobStep.job_id.in_(job_ids))
            ]
            stat_ids.extend(job_ids)
            stat_ids.extend(step_ids)

        if stat_ids:
            ItemStat.query.filter(
                ItemStat.item_id.in_(stat_ids),
            ).delete(synchronize_session=False)

        # remove any existing job data
        # TODO(dcramer): this is potentially fairly slow with cascades
        Job.query.filter(
            Job.build_id == build.id
        ).delete(synchronize_session=False)

        build.date_started = datetime.utcnow()
        build.date_modified = build.date_started
        build.date_finished = None
        build.duration = None
        build.status = Status.queued
        build.result = Result.unknown
        db.session.add(build)

        execute_build(build=build)

        return self.respond(build)
