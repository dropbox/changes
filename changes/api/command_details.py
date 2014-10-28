from __future__ import absolute_import

import json

from datetime import datetime
from flask_restful.reqparse import RequestParser
from sqlalchemy.sql import func

from changes.api.base import APIView
from changes.api.validators.datetime import ISODatetime
from changes.config import db, redis
from changes.constants import Status
from changes.expanders import CommandsExpander, TestsExpander
from changes.jobs.sync_job_step import sync_job_step
from changes.models import Command, CommandType, JobPhase, JobPlan


STATUS_CHOICES = ('queued', 'in_progress', 'finished')

EXPANDERS = {
    CommandType.collect_steps: CommandsExpander,
    CommandType.collect_tests: TestsExpander,
}


class CommandDetailsAPIView(APIView):
    post_parser = RequestParser()
    post_parser.add_argument('status', choices=STATUS_CHOICES)
    post_parser.add_argument('return_code', type=int)
    post_parser.add_argument('date', type=ISODatetime())
    # output is required for various collectors, and is the buffered response
    # of the command sent
    post_parser.add_argument('output', type=json.loads)

    def get(self, command_id):
        command = Command.query.get(command_id)
        if command is None:
            return '', 404

        return self.respond(command)

    def post(self, command_id):
        args = self.post_parser.parse_args()

        current_datetime = args.date or datetime.utcnow()

        # We need to lock this resource to ensure the command doesn't get expanded
        # twice in the time it's checking the attr + writing the updated value
        with redis.lock('expand:{}'.format(command_id), expire=3, nowait=True):
            command = Command.query.get(command_id)
            if command is None:
                return '', 404

            if command.status == Status.finished:
                return '{"error": "Command already marked as finished"}', 400

            if args.return_code is not None:
                command.return_code = args.return_code

            if args.status:
                command.status = Status[args.status]

                # if we've finished this job, lets ensure we have set date_finished
                if command.status == Status.finished and command.date_finished is None:
                    command.date_finished = current_datetime
                elif command.status != Status.finished and command.date_finished:
                    command.date_finished = None

                if command.status != Status.queued and command.date_started is None:
                    command.date_started = current_datetime
                elif command.status == Status.queued and command.date_started:
                    command.date_started = None

            db.session.add(command)
            db.session.flush()

        if args.output or args.status == 'finished':
            expander_cls = self.get_expander(command.type)
            if expander_cls is not None:
                if not args.output:
                    db.session.rollback()
                    return '{"error": "Missing output for command of type %s"}' % (command.type), 400

                expander = expander_cls(
                    project=command.jobstep.project,
                    data=args.output,
                )

                try:
                    expander.validate()
                except AssertionError as e:
                    db.session.rollback()
                    return '{"error": "{}"}'.format(e), 400
                except Exception:
                    db.session.rollback()
                    return '', 500

                self.expand_command(command, expander, args.output)

        db.session.commit()

        return self.respond(command)

    def get_expander(self, type):
        return EXPANDERS.get(type)

    def expand_command(self, command, expander, data):
        jobstep = command.jobstep
        phase_name = data.get('phase')
        if not phase_name:
            phase_count = db.session.query(
                func.count(),
            ).filter(
                JobPhase.job_id == jobstep.job_id,
            ).scalar()
            phase_name = 'Phase #{}'.format(phase_count)

        jobstep.data['expanded'] = True
        db.session.add(jobstep)

        new_jobphase = JobPhase(
            job_id=jobstep.job_id,
            project_id=jobstep.project_id,
            label=phase_name,
            status=Status.queued,
        )
        db.session.add(new_jobphase)

        _, buildstep = JobPlan.get_build_step_for_job(jobstep.job_id)

        results = []
        for future_jobstep in expander.expand(max_executors=jobstep.data['max_executors']):
            new_jobstep = buildstep.expand_jobstep(jobstep, new_jobphase, future_jobstep)
            results.append(new_jobstep)

        db.session.flush()

        for new_jobstep in results:
            sync_job_step.delay_if_needed(
                step_id=new_jobstep.id.hex,
                task_id=new_jobstep.id.hex,
                parent_task_id=new_jobphase.job.id.hex,
            )

        return results
