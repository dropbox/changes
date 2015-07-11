from __future__ import absolute_import

from datetime import datetime
from flask import current_app
from flask_restful.reqparse import RequestParser
from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.api.validators.datetime import ISODatetime
from changes.config import db
from changes.constants import Result, Status
from changes.db.utils import get_or_create
from changes.jobs.sync_job import sync_job
from changes.models import (
    Command, FailureReason, JobPhase, JobPlan, JobStep, Node, Plan, Snapshot, SnapshotImage,
)


RESULT_CHOICES = ('failed', 'passed', 'aborted', 'skipped')
STATUS_CHOICES = ('queued', 'in_progress', 'finished')

# Choices should map to Result/Status names. We don't just use
# the Enum names directly to make it harder to unintentionally
# broaden the public API.
assert set(RESULT_CHOICES) <= set(Result.__members__.keys())
assert set(STATUS_CHOICES) <= set(Status.__members__.keys())


class JobStepDetailsAPIView(APIView):
    post_parser = RequestParser()
    post_parser.add_argument('date', type=ISODatetime())
    post_parser.add_argument('status', choices=STATUS_CHOICES)
    post_parser.add_argument('result', choices=RESULT_CHOICES)
    post_parser.add_argument('node')
    post_parser.add_argument('heartbeat', type=bool)

    @classmethod
    def get_snapshot_image(self, current_snapshot_id, plan_id):
        """
        Get the snapshot image that should be used for a given plan.

        If the plan uses a dependent snapshot (that is, it uses a snapshot
        created by a different plan for its own build) then it returns
        the snapshot image associated with the plan it depends on, else
        it returns the snapshot image associated with the plan itself.
        """
        snapshot_plan_id = Plan.query.get(plan_id).snapshot_plan_id
        if snapshot_plan_id is None:
            snapshot_plan_id = plan_id

        return SnapshotImage.query.filter(
                    SnapshotImage.snapshot_id == current_snapshot_id,
                    SnapshotImage.plan_id == snapshot_plan_id,
               ).scalar()

    def _is_final_jobphase(self, jobphase):
        return not db.session.query(
            JobPhase.query.filter(
                JobPhase.date_created > jobphase.date_created,
            ).exists(),
        ).scalar()

    def get(self, step_id):
        jobstep = JobStep.query.options(
            joinedload('project', innerjoin=True),
        ).get(step_id)
        if jobstep is None:
            return '', 404

        jobplan = JobPlan.query.filter(
            JobPlan.job_id == jobstep.job_id,
        ).first()

        # determine if there's an expected snapshot outcome
        expected_image = SnapshotImage.query.filter(
            SnapshotImage.job_id == jobstep.job_id,
        ).first()

        current_image = None
        # we only send a current snapshot if we're not expecting to build
        # a new image
        if not expected_image:
            current_snapshot = Snapshot.get_current(jobstep.project_id)
            if current_snapshot and jobplan:
                current_image = self.get_snapshot_image(current_snapshot.id, jobplan.plan_id)
            elif current_app.config['DEFAULT_SNAPSHOT']:
                current_image = {
                    'id': current_app.config['DEFAULT_SNAPSHOT'],
                }

        context = self.serialize(jobstep)
        context['commands'] = self.serialize(list(jobstep.commands))
        context['snapshot'] = self.serialize(current_image)
        context['expectedSnapshot'] = self.serialize(expected_image)
        context['project'] = self.serialize(jobstep.project)

        return self.respond(context, serialize=False)

    def post(self, step_id):
        jobstep = JobStep.query.options(
            joinedload('project', innerjoin=True),
        ).get(step_id)
        if jobstep is None:
            return '', 404

        args = self.post_parser.parse_args()

        current_datetime = args.date or datetime.utcnow()

        if args.result:
            jobstep.result = Result[args.result]

        if args.status:
            jobstep.status = Status[args.status]

            # if we've finished this job, lets ensure we have set date_finished
            if jobstep.status == Status.finished and jobstep.date_finished is None:
                jobstep.date_finished = current_datetime
            elif jobstep.status != Status.finished and jobstep.date_finished:
                jobstep.date_finished = None

            if jobstep.status != Status.queued and jobstep.date_started is None:
                jobstep.date_started = current_datetime
            elif jobstep.status == Status.queued and jobstep.date_started:
                jobstep.date_started = None

        if args.node:
            node, _ = get_or_create(Node, where={
                'label': args.node,
            })
            jobstep.node_id = node.id

        # we want to guarantee that even if the jobstep seems to succeed, that
        # we accurately reflect what we internally would consider a success state
        if jobstep.result == Result.passed and jobstep.status == Status.finished:
            last_command = Command.query.filter(
                Command.jobstep_id == jobstep.id,
            ).order_by(Command.order.desc()).first()

            if not last_command:
                pass

            elif last_command.status != Status.finished:
                jobstep.result = Result.failed

            elif last_command.return_code != 0:
                jobstep.result = Result.failed

            # are we missing an expansion step? it must happen before reporting
            # the result, and would falsely give us a success metric
            elif last_command.type.is_collector() and self._is_final_jobphase(jobstep.phase):
                jobstep.result = Result.failed
                job = jobstep.job
                # TODO(dcramer): we should add a better failure reason
                db.session.add(FailureReason(
                    step_id=jobstep.id,
                    job_id=job.id,
                    build_id=job.build_id,
                    project_id=job.project_id,
                    reason='missing_artifact',
                ))

        db.session.add(jobstep)
        if db.session.is_modified(jobstep):
            db.session.commit()

            # TODO(dcramer): this is a little bit hacky, but until we can entirely
            # move to push APIs we need a good way to handle the existing sync
            job = jobstep.job
            sync_job.delay_if_needed(
                task_id=job.id.hex,
                parent_task_id=job.id.hex,
                job_id=job.build_id.hex,
            )

        return self.respond(jobstep)
