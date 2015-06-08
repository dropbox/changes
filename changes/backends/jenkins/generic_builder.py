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
        self.build_desc = current_app.config['CHANGES_CLIENT_BUILD_TYPES'][self.build_type]
        if self.build_desc.get('uses_client', False):
            if 'jenkins-command' not in self.build_desc:
                raise ValueError('build type %s missing required key: jenkins-command' % self.build_type)
            if 'adapter' not in self.build_desc:
                raise ValueError('build type %s missing required key: adapter' % self.build_type)

        self.commands = self.build_desc.get('commands', [])

        if not master_urls:
            # if we haven't specified master urls, lets try to take the default
            # for this given cluster
            master_urls = current_app.config['JENKINS_CLUSTERS'].get(self.cluster)

        super(JenkinsGenericBuilder, self).__init__(master_urls, *args, **kwargs)

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
                 'value': self.build_desc.get('pre-launch', '')},
                {'name': 'CHANGES_CLIENT_LXC_POST_LAUNCH',
                 'value': self.build_desc.get('post-launch', '')},
                {'name': 'CHANGES_CLIENT_LXC_RELEASE',
                 'value': self.build_desc.get('release', 'trusty')},
            ])

        return params

    def params_to_env(self, params):
        return {param['name']: param['value'] for param in params}

    def get_future_commands(self, params):
        return map(lambda command: FutureCommand(command['script'],
                                    env=self.params_to_env(params)),
                   self.commands)

    def create_commands(self, jobstep, params):
        index = 0
        for future_command in self.get_future_commands(params):
            db.session.add(future_command.as_command(jobstep, index))
            index += 1
