from __future__ import absolute_import, division, unicode_literals
import json
import logging

from uuid import UUID
from flask import request
from changes.api.base import APIView, error
from changes.config import db, statsreporter
from changes.constants import Result, Status
from changes.models.jobstep import JobStep


class JobStepNeedsAbortAPIView(APIView):
    def post(self):
        """
        Given a list of jobstep ids, returns the ids of those that should
        be aborted. This is a POST only because we're sending large-ish
        amounts of data--no state is changed by this call.
        """
        args = json.loads(request.data)

        try:
            jobstep_ids = args['jobstep_ids']
        except KeyError:
            return error('Missing jobstep_ids attribute')

        for id in jobstep_ids:
            try:
                UUID(id)
            except ValueError:
                err = "Invalid jobstep id sent to jobstep_needs_abort: %s"
                logging.warning(err, id, exc_info=True)
                return error(err % id)

        if len(jobstep_ids) == 0:
            return self.respond({'needs_abort': []})

        with statsreporter.stats().timer('jobstep_needs_abort'):
            finished = db.session.query(JobStep.id, JobStep.result, JobStep.data).filter(
                JobStep.status == Status.finished,
                JobStep.id.in_(jobstep_ids),
            ).all()

            needs_abort = []
            for (step_id, result, data) in finished:
                if result == Result.aborted or data.get('timed_out'):
                    needs_abort.append(step_id)

            return self.respond({'needs_abort': needs_abort})
