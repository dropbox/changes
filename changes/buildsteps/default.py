from __future__ import absolute_import

from changes.buildsteps.base import BuildStep
from changes.config import db
from changes.constants import Cause, Status
from changes.db.utils import get_or_create
from changes.jobs.sync_job_step import sync_job_step
from changes.models import CommandType, FutureCommand, JobPhase, JobStep


DEFAULT_ARTIFACTS = (
    'junit.xml',
    '*.junit.xml',
    'xunit.xml',
    '*.xunit.xml',
    'coverage.xml',
    '*.coverage.xml',
)

DEFAULT_PATH = './source/'

# TODO(dcramer): this doesnt make a lot of sense once we get off of LXC, so
# for now we're only stuffing it into JobStep.data
DEFAULT_RELEASE = 'precise'


class DefaultBuildStep(BuildStep):
    """
    A build step which relies on the a scheduling framework in addition to the
    Changes client (or some other push source).

    Jobs will get allocated via a polling step that is handled by the external
    scheduling framework. Once allocated a job is expected to begin reporting
    within a given timeout. All results are expected to be pushed via APIs.

    This build step is also responsible for generating appropriate commands
    in order for the client to obtain the source code.
    """
    def __init__(self, commands, path=DEFAULT_PATH, env=None,
                 artifacts=DEFAULT_ARTIFACTS, release=DEFAULT_RELEASE,
                 max_executors=20, **kwargs):
        command_defaults = (
            ('path', path),
            ('env', env),
            ('artifacts', artifacts),
        )
        for command in commands:
            for k, v in command_defaults:
                if k not in command:
                    command[k] = v
            if 'type' in command:
                command['type'] = CommandType[command['type']]
            else:
                command['type'] = CommandType.default

        self.env = env
        self.path = path
        self.release = release
        self.commands = map(lambda x: FutureCommand(**x), commands)
        self.max_executors = max_executors

        super(DefaultBuildStep, self).__init__(**kwargs)

    def get_label(self):
        return 'Build via Changes Client'

    def iter_all_commands(self, job):
        source = job.source
        repo = source.repository
        vcs = repo.get_vcs()
        if vcs is not None:
            yield FutureCommand(
                script=vcs.get_buildstep_clone(source, self.path),
                env=self.env,
                path='',
                artifacts=(),
            )

            if source.patch:
                yield FutureCommand(
                    script=vcs.get_buildstep_patch(source, self.path),
                    env=self.env,
                    path='',
                    artifacts=(),
                )

        for command in self.commands:
            yield command

    def execute(self, job):
        job.status = Status.queued
        db.session.add(job)

        phase, created = get_or_create(JobPhase, where={
            'job': job,
            'label': job.label,
        }, defaults={
            'status': Status.queued,
            'project': job.project,
        })

        step, created = get_or_create(JobStep, where={
            'phase': phase,
            'label': job.label,
        }, defaults={
            'status': Status.pending_allocation,
            'job': phase.job,
            'project': phase.project,
            'data': {
                'release': self.release,
                'max_executors': self.max_executors,
            },
        })

        # HACK(dcramer): we need to filter out non-setup commands
        # if we're running a snapshot build
        is_snapshot = job.build.cause == Cause.snapshot
        index = 0
        for future_command in self.iter_all_commands(job):
            if is_snapshot and future_command.type != CommandType.setup:
                continue

            index += 1
            command = future_command.as_command(
                jobstep=step,
                order=index,
            )
            db.session.add(command)

        db.session.commit()

        sync_job_step.delay(
            step_id=step.id.hex,
            task_id=step.id.hex,
            parent_task_id=job.id.hex,
        )

    def update(self, job):
        pass

    def update_step(self, step):
        """
        Look for allocated JobStep's and re-queue them if elapsed time is
        greater than allocation timeout.
        """
        # TODO(cramer):

    def cancel_step(self, step):
        pass
