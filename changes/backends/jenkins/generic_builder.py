from __future__ import absolute_import

from flask import current_app

from .builder import JenkinsBuilder


class JenkinsGenericBuilder(JenkinsBuilder):
    def __init__(self, master_urls=None, *args, **kwargs):
        self.script = kwargs.pop('script')
        self.cluster = kwargs.pop('cluster')
        self.diff_cluster = kwargs.pop('diff_cluster', None)
        self.path = kwargs.pop('path', '')
        self.workspace = kwargs.pop('workspace', '')

        if not master_urls:
            # if we haven't specified master urls, lets try to take the default
            # for this given cluster
            master_urls = current_app.config['JENKINS_CLUSTERS'].get(self.cluster)

        super(JenkinsGenericBuilder, self).__init__(master_urls, *args, **kwargs)

    def get_job_parameters(self, job, script=None, target_id=None, path=None):
        params = super(JenkinsGenericBuilder, self).get_job_parameters(
            job, target_id=target_id)

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

        params.extend([
            {'name': 'CHANGES_PID', 'value': project.slug},
            {'name': 'REPO_URL', 'value': repo_url},
            {'name': 'SCRIPT', 'value': script},
            {'name': 'REPO_VCS', 'value': repository.backend.name},
            {'name': 'CLUSTER', 'value': cluster},
            {'name': 'WORK_PATH', 'value': path},
            {'name': 'C_WORKSPACE', 'value': self.workspace},
        ])

        return params
