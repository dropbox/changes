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
    def __init__(self, commands=None, repo_path=None, path=None, env=None,
                 artifacts=DEFAULT_ARTIFACTS, release=DEFAULT_RELEASE,
                 max_executors=10, cpus=4, memory=8 * 1024, clean=True,
                 debug_config=None, test_stats_from=None, cluster=None,
                 **kwargs):
        """
        Constructor for DefaultBuildStep.

        Args:
            commands: list of commands that should be run. Run in the order given. Required.
            repo_path: The path to check out the repo to. Can be relative or absolute.
            path: The default path in which commands will be run. Can be absolute or
                relative to repo_path. If only one of repo_path and path is specified,
                both will be set to the same thing.
            cpus: How many cpus to limit the container to (not applicable for basic)
            memory: How much memory to limit the container to (not applicable for basic)
            clean: controls if the repository should be cleaned before
                tests are run.
                Defaults to true, because False may be unsafe; it may be
                useful to set to False if snapshots are in use and they
                intentionally leave useful incremental build products in the
                repository.
            debug_config: A dictionary of config options for either debugging
                or hacky features. In some cases these are passed through to
                changes-client, in other cases they change some behaviour on
                the server. Supported fields:
                  - infra_failures: this should be a dictionary and is used to
                    force infrastructure failures in builds. The keys of this
                    dictionary refer to the phase (possible values are
                    'primary' and 'expanded'), and the values are the
                    probabilities with which a JobStep in that phase will fail.
                    An example:
                      "debug_config": {"infra_failures": {"primary": 0.5}}
                    This will then cause an infra failure in the primary
                    JobStep with probability 0.5.
                  - prelaunch_script: passed to changes-client
                  - bind_mounts: passed to changes-client
                  - prefer_artifactstore: used in sync_job_step to select
                    artifact source when multiple sources are available
                  - repo_cache_dir: a directory on the build machine containing
                    local caches of repos; if the repository for this build is
                    found in repo_cache_dir, we may clone/pull from it rather
                    than from the normal remote repository. We currently don't
                    do anything to ensure that the cache is up to date;
                    configure e.g. a pre-launch script to do that.
            test_stats_from: project to get test statistics from, or
                None (the default) to use this project.  Useful if the
                project runs a different subset of tests each time, so
                test timing stats from the parent are not reliable.
            cluster: a cluster to associate jobs of this BuildStep with.
                Jobsteps will then only be run on slaves of the given cluster.
        """
        if commands is None:
            raise ValueError("Missing required config: need commands")
        if any(type(int_field) != int for int_field in (cpus, memory, max_executors)):
            raise ValueError("cpus, memory, and max_executors fields must be integers")

        if env is None:
            env = DEFAULT_ENV.copy()

        self.artifacts = artifacts
        self.env = env
        if repo_path:
            self.repo_path = repo_path
            # path is relative to repo_path (unless specified as an absolute path)
            self.path = os.path.join(repo_path, path) if path else repo_path
        else:
            # default repo_path to path if none specified
            self.repo_path = path or DEFAULT_PATH
            self.path = self.repo_path
        self.release = release
        self.max_executors = max_executors
        self.resources = {
            'cpus': cpus,
            'mem': memory,
        }
        self.clean = clean
        self.debug_config = debug_config or {}
        self.test_stats_from = test_stats_from
        self.cluster = cluster
        future_commands = []
        for command in commands:
            command_copy = command.copy()
            if 'type' in command_copy:
                command_copy['type'] = CommandType[command_copy['type']]
            future_command = FutureCommand(**command_copy)
            self._set_command_defaults(future_command)
            future_commands.append(future_command)
        self.commands = future_commands

        # this caches the snapshot image database object for a given job id.
        # we use it to avoid performing duplicate queries when
        # get_allocation_command() and get_allocation_params() are called.
        self._jobid2image = {}

        super(DefaultBuildStep, self).__init__(**kwargs)

    def get_label(self):
        return 'Build via Changes Client'

    def get_test_stats_from(self):
        return self.test_stats_from

    def _custom_bin_path(self):
        """The path in which to look for custom binaries we want to run.
        This is used in LXC where we bind mount custom binaries
        (currently only blacklist-remove)"""
        return ''

    def iter_all_commands(self, job):
        source = job.source
        repo = source.repository
        vcs = repo.get_vcs()
        if vcs is not None:
            pre_reset_command = self.debug_config.get('pre_reset_command', None)
            yield FutureCommand(
                script=vcs.get_buildstep_clone(
                        source, self.repo_path, self.clean,
                        self.debug_config.get('repo_cache_dir'),
                        pre_reset_command),
                env=self.env,
                type=CommandType.infra_setup,
            )

            if source.patch:
                yield FutureCommand(
                    script=vcs.get_buildstep_patch(source, self.repo_path),
                    env=self.env,
                    type=CommandType.infra_setup,
                )

        blacklist_remove_path = os.path.join(self._custom_bin_path(), 'blacklist-remove')
        yield FutureCommand(
            script=blacklist_remove_path + ' "' + job.project.get_config_path() + '"',
            path=self.repo_path,
            env=self.env,
            type=CommandType.infra_setup,
        )

        for command in self.commands:
            yield command

    def execute(self, job):
        job.status = Status.pending_allocation
        db.session.add(job)

        label = job.label
        if any(cmd.type.is_collector() for cmd in self.commands):
            label = 'Collect tests'

        # XXX(nate): we use the phase label for uniqueness, which isn't great.
        # We let the expanded phase pick its own phase name, so if someone
        # picked "Collect tests" for some reason, things would break.
        phase, _ = get_or_create(JobPhase, where={
            'job': job,
            'label': label,
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
            'label': phase.label,
        }
        if replaces:
            # if we're replacing an old jobstep, we specify new id in the where
            # clause to ensure we create a new jobstep, not just get the old one
            where['id'] = uuid.uuid4()

        step, _ = get_or_create(JobStep, where=where, defaults={
            'status': Status.pending_allocation,
            'job': phase.job,
            'project': phase.project,
            'cluster': self.cluster,
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
        for index, future_command in enumerate(all_commands):
            if not valid_command_pred(future_command.type):
                continue

            command = future_command.as_command(
                jobstep=step,
                order=index,
            )
            db.session.add(command)

        # TODO(dcramer): improve error handling here
        assert len(all_commands) != 0, "No commands were registered for build plan"

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

    def _set_command_defaults(self, future_command):
        if not future_command.artifacts:
            future_command.artifacts = self.artifacts
        future_command.path = os.path.join(self.path, future_command.path) if future_command.path else self.path
        c_env = self.env.copy()
        if future_command.env:
            c_env.update(future_command.env)
        future_command.env = c_env

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
        new_jobstep.cluster = self.cluster
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

            # set any needed defaults for expanded commands
            for future_command in future_jobstep.commands:
                self._set_command_defaults(future_command)

        # setup -> newly generated commands from expander -> teardown
        for index, future_command in enumerate(chain(setup_commands,
                                                     future_jobstep.commands,
                                                     teardown_commands)):
            new_command = future_command.as_command(new_jobstep, index)
            db.session.add(new_command)

        return new_jobstep

    def get_client_adapter(self):
        return 'basic'

    def _image_for_job_id(self, job_id):
        """
        Returns the SnapshotImage database object associated with the given
        job_id, or None if there is none (i.e. it isn't a snapshot build).
        The implementation caches this result so the query only has to be
        done once per job id.
        """
        if job_id not in self._jobid2image:
            expected_image = db.session.query(
                SnapshotImage.id,
            ).filter(
                SnapshotImage.job_id == job_id,
            ).scalar()
            # note that expected_image could be None
            self._jobid2image[job_id] = expected_image
        return self._jobid2image[job_id]

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
            'use-external-env': 'false',
        }

        if current_app.config['CLIENT_SENTRY_DSN']:
            params['sentry-dsn'] = current_app.config['CLIENT_SENTRY_DSN']

        if 'bind_mounts' in self.debug_config:
            params['bind-mounts'] = self.debug_config['bind_mounts']

        expected_image = self._image_for_job_id(jobstep.job_id)
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
            '-%s=%s' % (k, v)
            for k, v in params.iteritems()
        ))

    def get_artifact_manager(self, jobstep):
        return Manager([CoverageHandler, XunitHandler])

    def prefer_artifactstore(self):
        return self.debug_config.get('prefer_artifactstore', True)
