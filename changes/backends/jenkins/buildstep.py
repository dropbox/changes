from __future__ import absolute_import

import logging

from datetime import datetime, timedelta
from flask import current_app

from changes.artifacts.coverage import CoverageHandler
from changes.artifacts.xunit import XunitHandler
from changes.backends.base import UnrecoverableException
from changes.buildsteps.base import BuildStep
from changes.config import db
from changes.constants import Status

from .builder import JenkinsBuilder
from .generic_builder import JenkinsGenericBuilder


class JenkinsBuildStep(BuildStep):
    builder_cls = JenkinsBuilder
    logger = logging.getLogger('jenkins')

    def __init__(self, job_name=None, jenkins_url=None, jenkins_diff_url=None,
                 auth_keyname=None, verify=True, cluster=None, debug_config=None,
                 cpus=4, memory=8 * 1024):
        """
        The JenkinsBuildStep constructor here, which is used as a base
        for all Jenkins builds, only accepts parameters which are used
        to determine where and how to schedule the builds and does not
        deal with any of the logic regarding what to actually schedule
        on those jenkins masters.

        jenkins_url and jenkins_diff_url are either a single url or a list
        of possible jenkins masters for use of queueing. We don't worry
        about which slaves to schedule them on at this level.

        Args:
            auth_keyname: A key in the Changes config file that specifies the
                auth parameter to pass to the requests library. This could be
                a (username, password) tuple, in which case the requests library
                uses HTTPBasicAuth. For details, see http://docs.python-requests.org/en/latest/user/authentication/#basic-authentication
            verify (str or bool): The verify parameter to pass to the requests
                library for verifying SSL certificates. For details,
                see http://docs.python-requests.org/en/latest/user/advanced/#ssl-cert-verification
            cpus (int): Number of CPUs this buildstep requires to run.
            memory (int): Memory required for this buildstep in megabytes.
            cluster (Optional[str]): The Jenkins label to apply to be used to restrict the build to a subset of
                slaves where the master supports it.
            debug_config: A dictionary of debug config options. These are passed through
                to changes-client. There is also an infra_failures option, which takes a
                dictionary used to force infrastructure failures in builds. The keys of
                this dictionary refer to the phase (either 'primary' or 'expanded' if
                applicable), and the values are the probabilities with which
                a JobStep in that phase will fail.
                An example: "debug_config": {"infra_failures": {"primary": 0.5}}
                This will then cause an infra failure in the primary JobStep with
                probability 0.5.
        """
        # required field
        if job_name is None:
            raise ValueError("Missing required config: need job_name.")
        if any(int_field and type(int_field) != int for int_field in (cpus, memory)):
            raise ValueError("cpus and memory fields must be JSON ints")

        # we support a string or a list of strings for master server urls
        if not isinstance(jenkins_url, (list, tuple)):
            if jenkins_url:
                jenkins_url = [jenkins_url]
            else:
                jenkins_url = []

        if not isinstance(jenkins_diff_url, (list, tuple)):
            if jenkins_diff_url:
                jenkins_diff_url = [jenkins_diff_url]
            else:
                jenkins_diff_url = []

        self.job_name = job_name
        self.jenkins_urls = jenkins_url
        self.jenkins_diff_urls = jenkins_diff_url
        self.auth_keyname = auth_keyname
        self.verify = verify
        self.cluster = cluster
        self.debug_config = debug_config or {}

        self._resources = {}
        if cpus:
            self._resources['cpus'] = cpus
        if memory:
            self._resources['memory'] = memory

    def get_builder(self, app=current_app, **kwargs):
        """
        Any arguments passed in as kwargs will get passed in to the constructor
        for the builder associated with the buildstep. In particular we use this
        to override build_type.
        """
        args = self.get_builder_options().copy()
        args.update(kwargs)
        return self.builder_cls(app=app, **args)

    def get_builder_options(self):
        """
        A dictionary that is used as kwargs for creating the builder (these can be
        overridden in the kwargs of get_builder but this is not done very commonly),
        so most builder constructor values originate from the get_builder_options
        of the corresponding buildstep or one of its superclasses.
        """
        return {
            'master_urls': self.jenkins_urls,
            'diff_urls': self.jenkins_diff_urls,
            'job_name': self.job_name,
            'verify': self.verify,
            'auth_keyname': self.auth_keyname,
            'cluster': self.cluster,
            'debug_config': self.debug_config,
        }

    def get_label(self):
        return 'Execute job "{0}" on Jenkins'.format(self.job_name)

    def execute(self, job):
        """
        Creates a new job using the builder. This is where most of the
        logic is implemented for a given buildstep, but in this case the
        logic is handed to the builder.
        """
        builder = self.get_builder()
        builder.create_job(job)

    def update(self, job):
        builder = self.get_builder()
        builder.sync_job(job)

    def update_step(self, step):
        builder = self.get_builder()
        try:
            builder.sync_step(step)
        except UnrecoverableException:
            # bail if the step has been pending for too long as its likely
            # Jenkins fell over
            if step.date_created < datetime.utcnow() - timedelta(minutes=5):
                return
            raise

    def cancel_step(self, step):
        builder = self.get_builder()
        builder.cancel_step(step)

        step.status = Status.finished
        step.date_finished = datetime.utcnow()
        db.session.add(step)

    def create_replacement_jobstep(self, step):
        builder = self.get_builder()
        return builder.create_job(step.job, replaces=step)

    def fetch_artifact(self, artifact):
        """
        Processes a single artifact. Critical artifacts - that is, artifacts
        that are somehow special and possibly required - can be specified
        by overriding this method. It is not necessary to super all the way
        to here for critical artifacts, so this implementation is typically only
        used (and always used) for normal artifacts.
        """
        builder = self.get_builder()
        builder.sync_artifact(artifact)

    def can_snapshot(self):
        """
        Since we do most of our build_type logic in the builder rather than
        the buildstep, it makes sense to let the builder determine if it
        can snapshot or not. In particular, this means we have no need to
        actually look up and verify the buildtype from within the buildstep.
        """
        return self.get_builder().can_snapshot()

    def get_resource_limits(self):
        return self._resources.copy()

    def get_artifact_manager(self, jobstep):
        builder = self.get_builder()
        return builder.get_artifact_manager(jobstep)

    def verify_final_artifacts(self, jobstep, artifacts):
        builder = self.get_builder()
        return builder.verify_final_artifacts(jobstep, artifacts)

    def prefer_artifactstore(self):
        return self.debug_config.get('prefer_artifactstore', False)


SERVICE_LOG_FILE_PATTERNS = ('logged.service', '*.logged.service', 'service.log', '*.service.log')


class JenkinsGenericBuildStep(JenkinsBuildStep):
    builder_cls = JenkinsGenericBuilder

    def __init__(self, job_name=None, script=None, cluster=None, path='',
                 workspace='', reset_script='', build_type=None,
                 setup_script='', teardown_script='', clean=True,
                 artifacts=XunitHandler.FILENAMES + CoverageHandler.FILENAMES +
                 SERVICE_LOG_FILE_PATTERNS,
                 snapshot_script=None, **kwargs):
        """
        build_type describes how to use changes-client, but 'legacy'
        defaults to not using it at all. See configuration file
        for more details [CHANGES_CLIENT_BUILD_TYPES]
        workspace can be used to override where to check out the
        source tree and corresponds to the repository root
        once the build starts.

        The cluster and diff cluster arguments refer
        to Jenkins tags that are used to run the builds, so
        it should be made sure that slaves with these tags exist
        for the masters that are being used (See JenkinsBuildStep).

        path is relative to workspace and refers to where to change
        directory to after checking out the repository.

        setup_script, script, and teardown_script represent what to
        actually run. setup_script and teardown_script are always
        executed in the root of the repository (because of limitations
        regarding sharded builds documented elsewhere) while script
        is run from "path". teardown_script is always guaranteed
        to run regardless of whether script runs, but script will not
        run if setup_script fails. snapshot_script runs in place
        of script for snapshot builds.

        reset_script is used to asynchronously reset the workspace.

        `clean` controls if the repository should be cleaned before
        tests are run (requires integration with generic-build).
        Defaults to true, because False may be unsafe; it may be
        useful to set to False if snapshots are in use and they
        intentionally leave useful incremental build products in the
        repository.

        artifacts is a list of file name patterns describing the artifacts
        which need to be picked up by changes-client.
        """
        # required fields
        if None in (job_name, script, cluster):
            raise ValueError("Missing required config: need job_name, script, and cluster.")

        self.setup_script = setup_script
        self.script = script
        self.teardown_script = teardown_script
        self.reset_script = reset_script
        self.snapshot_script = snapshot_script
        self.path = path
        self.workspace = workspace
        self.build_type = build_type
        self.artifacts = artifacts
        self.clean = clean

        super(JenkinsGenericBuildStep, self).__init__(job_name=job_name, cluster=cluster, **kwargs)

    def get_lxc_config(self, jobstep):
        """
        Get the LXC configuration, if the LXC adapter should be used.
        Args:
            jobstep (JobStep): The JobStep to get the LXC config for.

        Returns:
            LXCConfig: The config to use for this jobstep, or None.
        """
        return self.get_builder().get_lxc_config(jobstep)

    def get_builder_options(self):
        options = super(JenkinsGenericBuildStep, self).get_builder_options()
        options.update({
            'setup_script': self.setup_script,
            'script': self.script,
            'teardown_script': self.teardown_script,
            'reset_script': self.reset_script,
            'snapshot_script': self.snapshot_script,
            'path': self.path,
            'workspace': self.workspace,
            'build_type': self.build_type,
            'artifacts': self.artifacts,
            'clean': self.clean,
        })
        return options
