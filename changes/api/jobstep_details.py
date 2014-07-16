from __future__ import absolute_import

from datetime import datetime
from flask_restful.reqparse import RequestParser
from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.config import db
from changes.constants import Result, Status
from changes.models import JobStep


RESULT_CHOICES = ('failed', 'passed')

STATUS_CHOICES = ('queued', 'in_progress', 'finished')


class JobStepDetailsAPIView(APIView):
    post_parser = RequestParser()
    post_parser.add_argument('status', choices=STATUS_CHOICES)
    post_parser.add_argument('result', choices=RESULT_CHOICES)

    def get(self, step_id):
        jobstep = JobStep.query.options(
            joinedload('project', innerjoin=True),
        ).get(step_id)
        if jobstep is None:
            return '', 404

        return self.respond(jobstep, serialize=False)

    def post(self, step_id):
        jobstep = JobStep.query.options(
            joinedload('project', innerjoin=True),
        ).get(step_id)
        if jobstep is None:
            return '', 404

        args = self.post_parser.parse_args()

        if args.result:
            jobstep.result = Result[args.result]

        if args.status:
            jobstep.status = Status[args.status]

            # if we've finished this job, lets ensure we have set date_finished
            if jobstep.status == Status.finished and jobstep.date_finished is None:
                jobstep.date_finished = datetime.utcnow()
            elif jobstep.status != Status.finished and jobstep.date_finished:
                jobstep.date_finished = None

            if jobstep.status != Status.queued and jobstep.date_started is None:
                jobstep.date_started = datetime.utcnow()
            elif jobstep.status == Status.queued and jobstep.date_started:
                jobstep.date_started = None

        db.session.add(jobstep)
        db.session.commit()

        return self.respond(jobstep, serialize=False)
