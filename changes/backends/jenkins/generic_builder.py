from __future__ import absolute_import

from flask import current_app

from changes.config import db
from changes.models.snapshot import SnapshotImage
from changes.models.command import FutureCommand
from changes.utils.http import build_uri
from changes.buildsteps.base import LXCConfig


from .builder import JenkinsBuilder


class JenkinsGenericBuilder(JenkinsBuilder):
    def __init__(self, master_urls=None, setup_script='', teardown_script='',
                 artifacts=(), reset_script='', diff_cluster=None, path='', workspace='',
                 snapshot_script=None, clean=True, *args, **kwargs):
        """Builder for JenkinsGenericBuildStep. See JenkinsGenericBuildStep
        for information on most of these arguments.
        """
        self.setup_script = setup_script
        self.script = kwargs.pop('script')
        self.teardown_script = teardown_script
        self.snapshot_script = snapshot_script
        self.reset_script = reset_script
        self.cluster = kwargs.pop('cluster')
        self.diff_cluster = diff_cluster
        self.path = path
        self.workspace = workspace
        self.artifacts = artifacts
        self.clean = clean

        # See configuration for more details; by default, the default build type is
        # legacy which sets up no additional configuration.
        self.build_type = kwargs.pop('build_type',
                                     current_app.config['CHANGES_CLIENT_DEFAULT_BUILD_TYPE'])
        if self.build_type is None:
            self.build_type = current_app.config['CHANGES_CLIENT_DEFAULT_BUILD_TYPE']

        # If a server url is not provided (default: None), set it to a blank string
        self.artifact_server_base_url = current_app.config['ARTIFACTS_SERVER'] or ''

        # we do this as early as possible in order to propagate the
        # error faster. The build description is simply the configuration
        # key'd by the build_type, documented in config.py
        self.build_desc = self.load_build_desc(self.build_type)

        super(JenkinsGenericBuilder, self).__init__(master_urls, *args, **kwargs)

    def load_build_desc(self, build_type):
        build_desc = current_app.config['CHANGES_CLIENT_BUILD_TYPES'][build_type]
        self.validate_build_desc(build_type, build_desc)
        return build_desc

    # TODO validate configuration at start of application or use a linter to validate
    # configuration before pushing/deploying
    def validate_build_desc(self, build_type, build_desc):
        if build_desc.get('uses_client', False):
            if 'jenkins-command' not in build_desc:
                raise ValueError('[CHANGES_CLIENT_BUILD_TYPES INVALID] build type %s missing required key: jenkins-command' % build_type)
            if 'adapter' not in build_desc:
                raise ValueError('[CHANGES_CLIENT_BUILD_TYPES INVALID] build type %s missing required key: adapter' % build_type)

    # These three methods all describe which build specification,
    # setup, and teardown should be used to create a snapshot
    # build. In the generic builder, this is the same as a normal build,
    # but sharded builds need to override these with the shard equivalents
    # in order to create the correct snapshot.
    def get_snapshot_build_desc(self):
        return self.build_desc

    def get_snapshot_setup_script(self):
        return self.setup_script

    def get_snapshot_teardown_script(self):
        return self.teardown_script

    def get_expected_image(self, job_id):
        """
        Get the snapshot-image (filesystem tarball for this jobstep).
        If this returns None, it is a normal build (the more common case),
        otherwise it returns the id of the snapshot image, which indicates
        to where the build agent should upload the snapshot onto s3.
        """
        return db.session.query(
            SnapshotImage.id,
        ).filter(
            SnapshotImage.job_id == job_id,
        ).scalar()

    def _get_build_desc(self, jobstep):
        if self.get_expected_image(jobstep.job_id):
            return self.get_snapshot_build_desc()
        return self.build_desc

    def get_lxc_config(self, jobstep):
        """
        Get the LXC configuration, if the LXC adapter should be used.
        Args:
            jobstep (JobStep): The JobStep to get the LXC config for.

        Returns:
            LXCConfig: The config to use for this jobstep, or None.
        """
        build_desc = self._get_build_desc(jobstep)
        if build_desc.get('uses_client') and build_desc.get('adapter') == 'lxc':
            app_cfg = current_app.config
            snapshot_bucket = app_cfg.get('SNAPSHOT_S3_BUCKET')
            default_pre = app_cfg.get('LXC_PRE_LAUNCH')
            default_post = app_cfg.get('LXC_POST_LAUNCH')
            default_release = app_cfg.get('LXC_RELEASE')
            return LXCConfig(s3_bucket=snapshot_bucket,
                             prelaunch=build_desc.get('pre-launch', default_pre),
                             postlaunch=build_desc.get('post-launch', default_post),
                             release=build_desc.get('release', default_release))
        return None

    def get_job_parameters(self, job, changes_bid, setup_script=None,
                           script=None, teardown_script=None, path=None):
        """
        Gets a list containing dictionaries, each with two keys - name and value.
        These key,value pairs correspond to the input variables in Jenkins.

        changes_bid is actually the jobstep id, and job is the current job.
        *_script and path override the corresponding fields of the current
        builder.
        """
        params = super(JenkinsGenericBuilder, self).get_job_parameters(
            job, changes_bid=changes_bid)

        if path is None:
            path = self.path

        if setup_script is None:
            setup_script = self.setup_script

        if script is None:
            script = self.script

        if teardown_script is None:
            teardown_script = self.teardown_script

        project = job.project
        repository = project.repository

        vcs = repository.get_vcs()
        if vcs:
            repo_url = vcs.remote_url
        else:
            repo_url = repository.url

        cluster = self.cluster
        is_diff = not job.source.is_commit()
        if is_diff and self.diff_cluster:
            cluster = self.diff_cluster

        snapshot_bucket = current_app.config.get('SNAPSHOT_S3_BUCKET', '') or ''

        default_pre = current_app.config.get('LXC_PRE_LAUNCH', '') or ''
        default_post = current_app.config.get('LXC_POST_LAUNCH', '') or ''
        default_release = current_app.config.get('LXC_RELEASE', 'trusty') or ''

        build_desc = self.build_desc

        # This is the image we are expected to produce or None
        # if this is not a snapshot build.
        expected_image = self.get_expected_image(job.id)

        # Setting script to be empty essentially forces nothing
        # but setup/teardown to be run, making a clean snapshot
        snapshot_id = ''
        if expected_image:
            snapshot_id = expected_image.hex

            # this is a no-op command in sh, essentially equivalent
            # to '' except it tells changes-client that we are
            # deliberately doing absolutely nothing. However,
            # if snapshot script is not None, then we just use
            # that in place of script (so the normal script is
            # never used).
            script = self.snapshot_script or ':'

            # sharded builds will have different setup/teardown/build_desc
            # scripts between shards and collector so we need to
            # use the shard ones
            build_desc = self.get_snapshot_build_desc()
            setup_script = self.get_snapshot_setup_script()
            teardown_script = self.get_snapshot_teardown_script()

        # CHANGES_BID, the jobstep id, is provided by superclass
        params.update({
            'CHANGES_PID': project.slug,
            'PROJECT_CONFIG': project.get_config_path(),
            'REPO_URL': repo_url,
            'SETUP_SCRIPT': setup_script,
            'SCRIPT': script,
            'TEARDOWN_SCRIPT': teardown_script,
            'RESET_SCRIPT': self.reset_script,
            'REPO_VCS': repository.backend.name,
            'CLUSTER': cluster,
            'WORK_PATH': path,
            'C_WORKSPACE': self.workspace,
            'ARTIFACTS_SERVER_BASE_URL': self.artifact_server_base_url})

        if build_desc.get('uses_client', False):
            params.update({
                'JENKINS_COMMAND': build_desc['jenkins-command'],
                'CHANGES_CLIENT_ADAPTER': build_desc['adapter'],
                'CHANGES_CLIENT_SERVER': build_uri('/api/0'),
                'CHANGES_CLIENT_SNAPSHOT_BUCKET': snapshot_bucket,
                'CHANGES_CLIENT_SNAPSHOT_ID': snapshot_id,
                'CHANGES_CLIENT_LXC_PRE_LAUNCH': build_desc.get('pre-launch',
                                                                default_pre),
                'CHANGES_CLIENT_LXC_POST_LAUNCH': build_desc.get('post-launch',
                                                                 default_post),
                'CHANGES_CLIENT_LXC_RELEASE': build_desc.get('release',
                                                             default_release)
            })

        return params

    def get_future_commands(self, env, commands, artifacts):
        """Create future commands which are later created as comands.
        See models/command.py.
        """
        return map(lambda command: FutureCommand(command['script'],
                                                 artifacts=artifacts,
                                                 env=env),
                   commands)

    def create_commands(self, jobstep, env):
        """
        This seems slightly redundant, but in fact is necessary for
        changes-client to work. The issue is mainly that the client is
        designed for the exact flow of information that mesos uses,
        in which the commands are taken from changes through an api request.
        We need to tell changes to run what would normally be ran through
        the Jenkins configuration - so we move this from the Jenkins
        configuration into the commands of the build type.

        Arguments:
          jobstep (JobStep): jobstep to create commands under
          env (dict): Env variables to supply to all commands.
        """
        commands = self.build_desc.get('commands', [])
        artifacts = self.artifacts_for_jobstep(jobstep)
        env = env.copy()
        if not self.clean:
            env['SKIP_GIT_CLEAN'] = "1"

        index = 0
        for future_command in self.get_future_commands(env, commands, artifacts):
            db.session.add(future_command.as_command(jobstep, index))
            index += 1

    def can_snapshot(self):
        """
        Whether or not this build can snapshot is purely a function of the
        build type. Right now the only adapter supporting this is the lxc
        adapter, but in the scenario that another adapter is added (e.g.
        docker?) then we would need for multiple adapters to supprt snapshots,
        so we just encode whether it can or not as a field, defaulting to
        false as most types don't support this operation.
        """
        return self.build_desc.get('can_snapshot', False)

    def artifacts_for_jobstep(self, jobstep):
        """
        The artifact names/patterns we want to collect for a given jobstep.

        For example, we may want to collect different artifacts for a
        collection phase jobstep.
        Arguments:
            jobstep (JobStep): jobstep in question
        """
        return self.artifacts
