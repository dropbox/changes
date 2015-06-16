from __future__ import absolute_import

from flask import current_app

from changes.config import db
from changes.models import FutureCommand
from changes.utils.http import build_uri

from .builder import JenkinsBuilder


class JenkinsGenericBuilder(JenkinsBuilder):
    def __init__(self, master_urls=None, *args, **kwargs):
        self.script = kwargs.pop('script')
        self.reset_script = kwargs.pop('reset_script', '')
        self.cluster = kwargs.pop('cluster')
        self.diff_cluster = kwargs.pop('diff_cluster', None)
        self.path = kwargs.pop('path', '')
        self.workspace = kwargs.pop('workspace', '')

        # See configuration for more details; by default, the default build type is
        # legacy which sets up no additional configuration.
        self.build_type = kwargs.pop('build_type',
            current_app.config['CHANGES_CLIENT_DEFAULT_BUILD_TYPE'])
        if self.build_type is None:
            self.build_type = current_app.config['CHANGES_CLIENT_DEFAULT_BUILD_TYPE']

        # we do this as early as possible in order to propagate the
        # error faster. The build description is simply the configuration
        # key'd by the build_type, documented in config.py
        self.build_desc = self.load_build_desc(self.build_type)

        if not master_urls:
            # if we haven't specified master urls, lets try to take the default
            # for this given cluster
            master_urls = current_app.config['JENKINS_CLUSTERS'].get(self.cluster)

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

    def get_job_parameters(self, job, changes_bid, script=None, path=None):
        params = super(JenkinsGenericBuilder, self).get_job_parameters(
            job, changes_bid=changes_bid)

        if path is None:
            path = self.path

        if script is None:
            script = self.script

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

        # CHANGES_BID, the jobstep id, is provided by superclass
        params.extend([
            {'name': 'CHANGES_PID', 'value': project.slug},
            {'name': 'REPO_URL', 'value': repo_url},
            {'name': 'SCRIPT', 'value': script},
            {'name': 'RESET_SCRIPT', 'value': self.reset_script},
            {'name': 'REPO_VCS', 'value': repository.backend.name},
            {'name': 'CLUSTER', 'value': cluster},
            {'name': 'WORK_PATH', 'value': path},
            {'name': 'C_WORKSPACE', 'value': self.workspace},
        ])
        if self.build_desc.get('uses_client', False):
            params.extend([
                {'name': 'JENKINS_COMMAND',
                 'value': self.build_desc['jenkins-command']},
                {'name': 'CHANGES_CLIENT_ADAPTER',
                 'value': self.build_desc['adapter']},
                {'name': 'CHANGES_CLIENT_SERVER',
                 'value': build_uri('/api/0')},
                {'name': 'CHANGES_CLIENT_SNAPSHOT_BUCKET',
                 'value': snapshot_bucket},
                {'name': 'CHANGES_CLIENT_SNAPSHOT_ID', 'value': ''},
                {'name': 'CHANGES_CLIENT_LXC_PRE_LAUNCH',
                 'value': self.build_desc.get('pre-launch', default_pre)},
                {'name': 'CHANGES_CLIENT_LXC_POST_LAUNCH',
                 'value': self.build_desc.get('post-launch', default_post)},
                {'name': 'CHANGES_CLIENT_LXC_RELEASE',
                 'value': self.build_desc.get('release', default_release)},
            ])

        return params

    def params_to_env(self, params):
        return {param['name']: param['value'] for param in params}

    def get_future_commands(self, params, commands):
        return map(lambda command: FutureCommand(command['script'],
                                    env=self.params_to_env(params)),
                   commands)

    def create_commands(self, jobstep, params):
        commands = self.build_desc.get('commands', [])

        index = 0
        for future_command in self.get_future_commands(params, commands):
            db.session.add(future_command.as_command(jobstep, index))
            index += 1
