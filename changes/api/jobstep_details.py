from __future__ import absolute_import

import json

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
from changes.jobs.sync_job_step import is_final_jobphase
from changes.models import (
    Command, FailureReason, JobPlan, JobStep, Node, SnapshotImage,
)


RESULT_CHOICES = ('failed', 'passed', 'aborted', 'skipped', 'infra_failed')
STATUS_CHOICES = ('queued', 'in_progress', 'finished')

# Choices should map to Result/Status names. We don't just use
# the Enum names directly to make it harder to unintentionally
# broaden the public API and because not all options necessarily
# make sense for this interface.
assert set(RESULT_CHOICES) <= set(Result.__members__.keys())
assert set(STATUS_CHOICES) <= set(Status.__members__.keys())


class JobStepDetailsAPIView(APIView):
    post_parser = RequestParser()
    post_parser.add_argument('date', type=ISODatetime())
    post_parser.add_argument('status', choices=STATUS_CHOICES)
    post_parser.add_argument('result', choices=RESULT_CHOICES)
    post_parser.add_argument('node')
    post_parser.add_argument('heartbeat', type=bool)
    post_parser.add_argument('metrics')

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
            current_image = None
            if jobplan:
                current_image = jobplan.snapshot_image
            if current_image is None and current_app.config['DEFAULT_SNAPSHOT']:
                current_image = {
                    'id': current_app.config['DEFAULT_SNAPSHOT'],
                }

        context = self.serialize(jobstep)
        context['commands'] = self.serialize(list(jobstep.commands))
        context['snapshot'] = self.serialize(current_image)
        context['expectedSnapshot'] = self.serialize(expected_image)
        context['project'] = self.serialize(jobstep.project)
        context['job'] = self.serialize(jobstep.job)

        _, buildstep = JobPlan.get_build_step_for_job(jobstep.job_id)
        resource_limits = buildstep.get_resource_limits() if buildstep else {}
        if resource_limits:
            context['resourceLimits'] = resource_limits

        lxc_config = buildstep.get_lxc_config(jobstep) if buildstep else None
        if lxc_config:
            context["adapter"] = "lxc"
            lxc_config = {
                'preLaunch': lxc_config.prelaunch,
                'postLaunch': lxc_config.postlaunch,
                's3Bucket': lxc_config.s3_bucket,
                'compression': lxc_config.compression,
                'release': lxc_config.release,
            }
            context['lxcConfig'] = lxc_config

        debugConfig = buildstep.debug_config if buildstep else {}
        if 'debugForceInfraFailure' in jobstep.data:
            debugConfig['forceInfraFailure'] = jobstep.data['debugForceInfraFailure']
        if debugConfig:
            context['debugConfig'] = self.serialize(debugConfig)

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

        if args.metrics:
            try:
                metrics = json.loads(args.metrics)
            except ValueError:
                return {'message': 'Metrics was not valid JSON'}, 400
            if not isinstance(metrics, dict):
                return {'message': 'Metrics should be a JSON object'}, 400
            if 'metrics' in jobstep.data:
                jobstep.data['metrics'].update(metrics)
            else:
                jobstep.data['metrics'] = metrics

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
            elif last_command.type.is_collector() and is_final_jobphase(jobstep.phase):
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
                job_id=job.id.hex,
                task_id=job.id.hex,
                parent_task_id=job.build_id.hex,
            )
        elif args.metrics:
            # Check for args.metrics because is_modified doesn't detect if data['metrics'] gets updated.
            # is_modified works fine for map creation, but not map updation.
            db.session.commit()

        return self.respond(jobstep)
