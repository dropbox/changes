from __future__ import absolute_import

from copy import deepcopy
from itertools import chain

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

DEFAULT_ENV = {}


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
    # TODO(dcramer): we need to enforce ordering of setup/teardown commands
    # so that setup is always first and teardown is always last. Realistically
    # this should be something we abstract away in the UI so that there are
    # just three command phases entered
    def __init__(self, commands, path=DEFAULT_PATH, env=None,
                 artifacts=DEFAULT_ARTIFACTS, release=DEFAULT_RELEASE,
                 max_executors=20, **kwargs):

        if env is None:
            env = DEFAULT_ENV.copy()

        for command in commands:
            if 'artifacts' not in command:
                command['artifacts'] = artifacts

            if 'path' not in command:
                command['path'] = path

            c_env = env.copy()
            if 'env' in command:
                for key, value in command['env'].items():
                    c_env[key] = value
            command['env'] = c_env

            if 'type' in command:
                command['type'] = CommandType[command['type']]
            else:
                command['type'] = CommandType.default

        self.env = env
        self.path = path
        self.release = release
        self.commands = commands
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
                type=CommandType.setup,
            )

            if source.patch:
                yield FutureCommand(
                    script=vcs.get_buildstep_patch(source, self.path),
                    env=self.env,
                    type=CommandType.setup,
                )

        for command in self.commands:
            yield FutureCommand(**command)

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
            if is_snapshot and future_command.type not in (CommandType.setup, CommandType.teardown):
                continue

            index += 1
            command = future_command.as_command(
                jobstep=step,
                order=index,
            )
            db.session.add(command)

        # TODO(dcramer): improve error handling here
        assert index != 0, "No commands were registered for build plan"

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

    def expand_jobstep(self, jobstep, new_jobphase, future_jobstep):
        new_jobstep = future_jobstep.as_jobstep(new_jobphase)

        base_jobstep_data = deepcopy(jobstep.data)

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

        # when we expand the command we need to include all setup and teardown
        # commands as part of the build step
        setup_commands = []
        teardown_commands = []
        for future_command in self.iter_all_commands(jobstep.job):
            if future_command.type == CommandType.setup:
                setup_commands.append(future_command)
            elif future_command.type == CommandType.teardown:
                teardown_commands.append(future_command)

        # setup -> newly generated commands from expander -> teardown
        for index, command in enumerate(chain(setup_commands,
                                              future_jobstep.commands,
                                              teardown_commands)):
            new_command = command.as_command(new_jobstep, index)
            db.session.add(new_command)

        return new_jobstep
