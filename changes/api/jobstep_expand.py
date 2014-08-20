from __future__ import absolute_import

import json

from copy import deepcopy
from flask_restful.reqparse import RequestParser
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func

from changes.api.base import APIView
from changes.config import db, redis
from changes.constants import Status
from changes.expanders import CommandsExpander, TestsExpander
from changes.jobs.sync_job_step import sync_job_step
from changes.models import JobPhase, JobStep


EXPAND_TYPES = ('steps', 'tests')

EXPANDERS = {
    'commands': CommandsExpander,
    'tests': TestsExpander,
}


class JobStepExpandAPIView(APIView):
    post_parser = RequestParser()
    post_parser.add_argument('type', choices=EXPAND_TYPES, required=True)
    post_parser.add_argument('data', type=json.loads, required=True)

    def get_expander(self, type):
        return EXPANDERS[type]

    def post(self, step_id):
        """
        Given a parent JobStep, expand the Job into N more JobSteps (which will
        implicitly create the next JobPhase).

        The ``type`` value dictates what kind of expansion is happening, which
        is then used to validate the ``data`` payload.

        Two expansion types are currently available:

        commands:
          Creates new JobSteps which execute simple commands.

        tests:
          Creates new JobSteps which execute the given test suite, specified
          by a command, and partitioned by Changes' internal test distribution
          logic.
        """

        # We need to lock this resource to ensure the jobstep doesn't get expanded
        # twice in the time it's checking the attr + writing the updated value
        with redis.lock('expand:{}'.format(step_id), expire=60, nowait=True):
            jobstep = JobStep.query.options(
                joinedload('project', innerjoin=True),
            ).get(step_id)
            if jobstep is None:
                return '', 404

            if jobstep.data.get('expanded'):
                return '{"error": "Job step has already been expanded"}', 400

            args = self.post_parser.parse_args()

            expander = self.get_expander(args.type)(
                project=jobstep.project,
                data=args.data,
            )

            try:
                expander.validate()
            except AssertionError as e:
                return '{"error": "{}"}'.format(e), 400
            except Exception:
                return '', 500

            phase_name = args.data.get('phase')
            if not phase_name:
                phase_count = db.session.query(
                    func.count(),
                ).filter(
                    JobPhase.job_id == jobstep.job_id,
                ).scalar()
                phase_name = 'Phase #{}'.format(phase_count)

            base_jobstep_data = deepcopy(jobstep.data)

            jobstep.data['expanded'] = True
            db.session.add(jobstep)
            db.session.flush()

        new_jobphase = JobPhase(
            job_id=jobstep.job_id,
            project_id=jobstep.project_id,
            label=phase_name,
            status=Status.queued,
        )
        db.session.add(new_jobphase)

        results = []
        for future_jobstep in expander.expand(max_executors=jobstep.data['max_executors']):
            new_jobstep = future_jobstep.as_jobstep(new_jobphase)
            # TODO(dcramer): realistically we should abstract this into the
            # BuildStep interface so it can dictate how the job is created
            # and fired.
            new_jobstep.status = Status.pending_allocation
            # inherit base properties from parent jobstep
            for key, value in base_jobstep_data.items():
                if key not in new_jobstep.data:
                    new_jobstep.data[key] = value
            new_jobstep.data['generated'] = True
            db.session.add(new_jobstep)

            for index, command in enumerate(future_jobstep.commands):
                new_command = command.as_command(new_jobstep, index)
                db.session.add(new_command)

            results.append(new_jobstep)

        db.session.commit()

        for new_jobstep in results:
            sync_job_step.delay_if_needed(
                step_id=new_jobstep.id.hex,
                task_id=new_jobstep.id.hex,
                parent_task_id=new_jobphase.job.id.hex,
            )

        return self.respond(results)
