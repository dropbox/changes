from __future__ import absolute_import

import os
import uuid

from copy import deepcopy
from flask import current_app
from itertools import chain

from changes.artifacts.coverage import CoverageHandler
from changes.artifacts.manager import Manager
from changes.artifacts.xunit import XunitHandler
from changes.buildsteps.base import BuildStep, LXCConfig
from changes.config import db
from changes.constants import Cause, Status
from changes.db.utils import get_or_create
from changes.jobs.sync_job_step import sync_job_step
from changes.models import (
    CommandType, FutureCommand, JobPhase, SnapshotImage
)
from changes.models.jobstep import JobStep, FutureJobStep

from changes.utils.http import build_uri


DEFAULT_ARTIFACTS = XunitHandler.FILENAMES + CoverageHandler.FILENAMES

DEFAULT_PATH = './source/'

# TODO(dcramer): this doesnt make a lot of sense once we get off of LXC, so
# for now we're only stuffing it into JobStep.data
DEFAULT_RELEASE = 'precise'

DEFAULT_ENV = {
    'CHANGES': '1',
}

# We only want to copy certain attributes from a jobstep (basically, only
# static state, not things that change after jobstep creation), so we
# have an explicit list of attributes we'll copy
JOBSTEP_DATA_COPY_WHITELIST = ('release', 'cpus', 'memory', 'weight', 'tests', 'shard_count')


class DefaultBuildStep(BuildStep):
    """
    A build step which relies on a scheduling framework in addition to the
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
    # just three command phases entered. We should **probably** just have
    # commands be specified in different arrays:
    # - setup_commands
    # - collect_commands
    # - commands
    # - teardown_commands
    def __init__(self, commands=None, path=DEFAULT_PATH, env=None,
                 artifacts=DEFAULT_ARTIFACTS, release=DEFAULT_RELEASE,
                 max_executors=10, cpus=4, memory=8 * 1024, clean=True,
                 debug_config=None, test_stats_from=None,
                 **kwargs):
        """
        Constructor for DefaultBuildStep.

        Args:
            cpus: How many cpus to limit the container to (not applicable for basic)
            memory: How much memory to limit the container to (not applicable for basic)
            clean: controls if the repository should be cleaned before
                tests are run.
                Defaults to true, because False may be unsafe; it may be
                useful to set to False if snapshots are in use and they
                intentionally leave useful incremental build products in the
                repository.
            debug_config: A dictionary of debug config options. These are passed through
                to changes-client. There is also an infra_failures option, which takes a
                dictionary used to force infrastructure failures in builds. The keys of
                this dictionary refer to the phase (for DefaultBuildSteps, only possible
                value is 'primary'), and the values are the probabilities with which
                a JobStep in that phase will fail.
                An example: "debug_config": {"infra_failures": {"primary": 0.5}}
                This will then cause an infra failure in the primary JobStep with
                probability 0.5.
            test_stats_from: project to get test statistics from, or
                None (the default) to use this project.  Useful if the
                project runs a different subset of tests each time, so
                test timing stats from the parent are not reliable.
        """
        if commands is None:
            raise ValueError("Missing required config: need commands")

        if env is None:
            env = DEFAULT_ENV.copy()

        self.artifacts = artifacts
        for command in commands:
            if 'artifacts' not in command:
                command['artifacts'] = self.artifacts

            command['path'] = os.path.join(path, command.get('path', ''))

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
        self.resources = {
            'cpus': cpus,
            'mem': memory,
        }
        self.clean = clean
        self.debug_config = debug_config or {}
        self.test_stats_from = test_stats_from

        super(DefaultBuildStep, self).__init__(**kwargs)

    def get_label(self):
        return 'Build via Changes Client'

    def get_test_stats_from(self):
        return self.test_stats_from

    def iter_all_commands(self, job):
        source = job.source
        repo = source.repository
        vcs = repo.get_vcs()
        if vcs is not None:
            yield FutureCommand(
                script=vcs.get_buildstep_clone(source, self.path, self.clean),
                env=self.env,
                type=CommandType.infra_setup,
            )

            if source.patch:
                yield FutureCommand(
                    script=vcs.get_buildstep_patch(source, self.path),
                    env=self.env,
                    type=CommandType.infra_setup,
                )

        for command in self.commands:
            yield FutureCommand(**command)

    def execute(self, job):
        job.status = Status.pending_allocation
        db.session.add(job)

        phase, _ = get_or_create(JobPhase, where={
            'job': job,
            'label': job.label,
        }, defaults={
            'status': Status.pending_allocation,
            'project': job.project,
        })

        self._setup_jobstep(phase, job)

    def _setup_jobstep(self, phase, job, replaces=None):
        """
        Does the work of setting up (or recreating) the single jobstep for a build.

        Args:
            phase (JobPhase): phase this JobStep will be part of
            job (Job): the job this JobStep will be part of
            replaces (JobStep): None for new builds, otherwise the (failed)
                                JobStep that this JobStep will replace.
        Returns:
            The newly created JobStep
        """
        where = {
            'phase': phase,
            'label': job.label,
        }
        if replaces:
            # if we're replacing an old jobstep, we specify new id in the where
            # clause to ensure we create a new jobstep, not just get the old one
            where['id'] = uuid.uuid4()

        step, _ = get_or_create(JobStep, where=where, defaults={
            'status': Status.pending_allocation,
            'job': phase.job,
            'project': phase.project,
            'data': {
                'release': self.release,
                'max_executors': self.max_executors,
                'cpus': self.resources['cpus'],
                'mem': self.resources['mem'],
            },
        })
        BuildStep.handle_debug_infra_failures(step, self.debug_config, 'primary')

        all_commands = list(self.iter_all_commands(job))

        # we skip certain commands for e.g. collection JobSteps.
        valid_command_pred = CommandType.is_valid_for_default
        if job.build.cause == Cause.snapshot:
            valid_command_pred = CommandType.is_valid_for_snapshot
        elif any(fc.type.is_collector() for fc in all_commands):
            valid_command_pred = CommandType.is_valid_for_collection
        index = 0
        for future_command in all_commands:
            if not valid_command_pred(future_command.type):
                continue

            index += 1
            command = future_command.as_command(
                jobstep=step,
                order=index,
            )
            db.session.add(command)

        # TODO(dcramer): improve error handling here
        assert index != 0, "No commands were registered for build plan"

        if replaces:
            replaces.replacement_id = step.id
            db.session.add(replaces)

        db.session.commit()

        sync_job_step.delay(
            step_id=step.id.hex,
            task_id=step.id.hex,
            parent_task_id=job.id.hex,
        )

        return step

    def create_replacement_jobstep(self, step):
        if not step.data.get('expanded', False):
            return self._setup_jobstep(step.phase, step.job, replaces=step)
        future_commands = map(FutureCommand.from_command, step.commands)
        future_jobstep = FutureJobStep(step.label, commands=future_commands)
        # we skip adding setup and teardown commands because these will already
        # be present in the old, failed JobStep.
        new_jobstep = self.create_expanded_jobstep(step, step.phase, future_jobstep,
                                   skip_setup_teardown=True)
        db.session.flush()
        step.replacement_id = new_jobstep.id
        db.session.add(step)
        db.session.commit()
        sync_job_step.delay_if_needed(
            step_id=new_jobstep.id.hex,
            task_id=new_jobstep.id.hex,
            parent_task_id=new_jobstep.job.id.hex,
        )
        return new_jobstep

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

    def create_expanded_jobstep(self, base_jobstep, new_jobphase, future_jobstep, skip_setup_teardown=False):
        """
        Converts an expanded FutureJobstep into a JobStep and sets up its commands accordingly.

        Args:
            base_jobstep: The base JobStep to copy data attributes from.
            new_jobphase: The JobPhase for the new JobStep
            future_jobstep: the FutureJobstep to convert from.
            skip_setup_teardown: if True, don't add setup and teardown commands
                to the new JobStep (e.g., if future_jobstep already has them)
        Returns the newly created JobStep (uncommitted).
        """
        new_jobstep = future_jobstep.as_jobstep(new_jobphase)

        base_jobstep_data = deepcopy(base_jobstep.data)

        # inherit base properties from parent jobstep
        for key, value in base_jobstep_data.items():
            if key not in JOBSTEP_DATA_COPY_WHITELIST:
                continue
            if key not in new_jobstep.data:
                new_jobstep.data[key] = value
        new_jobstep.status = Status.pending_allocation
        new_jobstep.data['expanded'] = True
        BuildStep.handle_debug_infra_failures(new_jobstep, self.debug_config, 'expanded')
        db.session.add(new_jobstep)

        # when we expand the command we need to include all setup and teardown
        # commands
        setup_commands = []
        teardown_commands = []
        # TODO(nate): skip_setup_teardown really means "we're whitewashing this jobstep"
        # since we also don't set the command's path in those cases.
        if not skip_setup_teardown:
            for future_command in self.iter_all_commands(base_jobstep.job):
                if future_command.type.is_setup():
                    setup_commands.append(future_command)
                elif future_command.type == CommandType.teardown:
                    teardown_commands.append(future_command)

            for future_command in future_jobstep.commands:
                future_command.path = os.path.join(self.path, future_command.path or '')

        # setup -> newly generated commands from expander -> teardown
        for index, future_command in enumerate(chain(setup_commands,
                                                     future_jobstep.commands,
                                                     teardown_commands)):
            new_command = future_command.as_command(new_jobstep, index)
            # TODO(dcramer): this API isn't really ideal. Future command should
            # set things to NoneType and we should deal with unset values
            if not new_command.artifacts:
                new_command.artifacts = self.artifacts
            db.session.add(new_command)

        return new_jobstep

    def get_client_adapter(self):
        return 'basic'

    def get_allocation_params(self, jobstep):
        params = {
            'artifact-search-path': self.path,
            'artifacts-server': current_app.config['ARTIFACTS_SERVER'],
            'adapter': self.get_client_adapter(),
            'server': build_uri('/api/0/'),
            'jobstep_id': jobstep.id.hex,
            's3-bucket': current_app.config['SNAPSHOT_S3_BUCKET'],
            'pre-launch': self.debug_config.get('prelaunch_script') or current_app.config['LXC_PRE_LAUNCH'],
            'post-launch': current_app.config['LXC_POST_LAUNCH'],
            'release': self.release,
        }

        if current_app.config['CLIENT_SENTRY_DSN']:
            params['sentry-dsn'] = current_app.config['CLIENT_SENTRY_DSN']

        if 'bind_mounts' in self.debug_config:
            params['bind-mounts'] = self.debug_config['bind_mounts']

        # TODO(dcramer): we need some kind of tie into the JobPlan in order
        # to dictate that this is a snapshot build
        # determine if there's an expected snapshot outcome
        expected_image = db.session.query(
            SnapshotImage.id,
        ).filter(
            SnapshotImage.job_id == jobstep.job_id,
        ).scalar()
        if expected_image:
            params['save-snapshot'] = expected_image.hex

        # Filter out any None-valued parameter
        return dict((k, v) for k, v in params.iteritems() if v is not None)

    def get_lxc_config(self, jobstep):
        """
        Get the LXC configuration, if the LXC adapter should be used.
        Args:
            jobstep (JobStep): The JobStep to get the LXC config for.

        Returns:
            LXCConfig: The config to use for this jobstep, or None.
        """
        if self.get_client_adapter() == "lxc":
            app_cfg = current_app.config
            return LXCConfig(s3_bucket=app_cfg['SNAPSHOT_S3_BUCKET'],
                             prelaunch=self.debug_config.get('prelaunch_script') or app_cfg['LXC_PRE_LAUNCH'],
                             postlaunch=app_cfg['LXC_POST_LAUNCH'],
                             compression=None,
                             release=self.release)
        return None

    def get_resource_limits(self):
        return {'memory': self.resources['mem'],
                'cpus': self.resources['cpus']}

    def get_allocation_command(self, jobstep):
        params = self.get_allocation_params(jobstep)
        return 'changes-client %s' % (' '.join(
            '-%s %s' % (k, v)
            for k, v in params.iteritems()
        ))

    def get_artifact_manager(self, jobstep):
        return Manager([CoverageHandler, XunitHandler])

    def prefer_artifactstore(self):
        return self.debug_config.get('prefer_artifactstore', True)
