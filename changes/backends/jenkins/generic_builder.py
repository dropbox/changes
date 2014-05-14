from .builder import JenkinsBuilder


class JenkinsGenericBuilder(JenkinsBuilder):
    def __init__(self, *args, **kwargs):
        self.script = kwargs.pop('script')
        self.cluster = kwargs.pop('cluster')
        super(JenkinsGenericBuilder, self).__init__(*args, **kwargs)

    def get_job_parameters(self, job, script=None, target_id=None, path=''):
        params = super(JenkinsGenericBuilder, self).get_job_parameters(
            job, target_id=target_id)

        if script is None:
            script = self.script

        project = job.project
        repository = project.repository

        vcs = repository.get_vcs()
        if vcs:
            repo_url = vcs.remote_url
        else:
            repo_url = repository.url

        params.extend([
            {'name': 'CHANGES_PID', 'value': project.slug},
            {'name': 'REPO_URL', 'value': repo_url},
            {'name': 'SCRIPT', 'value': script},
            {'name': 'REPO_VCS', 'value': repository.backend.name},
            {'name': 'CLUSTER', 'value': self.cluster},
            {'name': 'WORK_PATH', 'value': path},
        ])

        return params
