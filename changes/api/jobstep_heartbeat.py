from __future__ import absolute_import

from datetime import datetime
from flask_restful.reqparse import RequestParser

from changes.api.base import APIView, error
from changes.api.validators.datetime import ISODatetime
from changes.config import db
from changes.constants import Result
from changes.models.jobstep import JobStep


class JobStepHeartbeatAPIView(APIView):
    post_parser = RequestParser()
    post_parser.add_argument('date', type=ISODatetime())

    def post(self, step_id):
        jobstep = JobStep.query.get(step_id)
        if jobstep is None:
            return error("Not found", http_code=404)

        # NOTE(josiah): we think this is okay as is, but it might be better to
        # report infra_failure the same way as aborted.
        if jobstep.result == Result.aborted:
            return error("Aborted", http_code=410)

        args = self.post_parser.parse_args()

        current_datetime = args.date or datetime.utcnow()

        jobstep.last_heartbeat = current_datetime
        db.session.add(jobstep)
        db.session.commit()

        return self.respond(jobstep)
