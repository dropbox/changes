from __future__ import absolute_import

from datetime import datetime
from flask_restful.reqparse import RequestParser
from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.api.validators.datetime import ISODatetime
from changes.config import db
from changes.constants import Result, Status
from changes.db.utils import get_or_create
from changes.jobs.sync_job import sync_job
from changes.models import JobPlan, JobStep, Node, Snapshot, SnapshotImage


RESULT_CHOICES = ('failed', 'passed')

STATUS_CHOICES = ('queued', 'in_progress', 'finished')


class JobStepDetailsAPIView(APIView):
    post_parser = RequestParser()
    post_parser.add_argument('date', type=ISODatetime())
    post_parser.add_argument('status', choices=STATUS_CHOICES)
    post_parser.add_argument('result', choices=RESULT_CHOICES)
    post_parser.add_argument('node')

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
                current_image = SnapshotImage.query.filter(
                    SnapshotImage.snapshot_id == current_snapshot.id,
                    SnapshotImage.plan_id == jobplan.plan_id,
                ).first()

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
